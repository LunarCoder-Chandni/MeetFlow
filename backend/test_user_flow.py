import os, tempfile, unittest, subprocess, sys
from unittest.mock import patch

fd, path = tempfile.mkstemp(suffix='.db')
os.close(fd)
os.environ['DATABASE_PATH'] = path
os.environ['ORGANIZATION_DATA_DIR'] = path + '-orgs'
os.environ['AUTH_DATABASE_PATH'] = __import__('os').path.join(path + '-orgs', 'accounts.db')
os.environ['GEMINI_API_KEY'] = ''
import app as A

TRANSCRIPTS = [
    'Mira: We agree the exhibition budget is $8,000. Leo: The venue will be the North Hall. Mira: I will book the hall by April 8, 2027. Leo: We need a safety plan.',
    'Mira: We must revise the exhibition budget to $9,500. Leo: Agreed.',
    'Leo: We confirm that the venue remains the North Hall.'
]

def extraction(i):
    decisions = [
        [{'topic':'Exhibition Budget','value':'$8,000','speaker':'Mira','quote':'We agree the exhibition budget is $8,000.'}, {'topic':'Venue','value':'North Hall','speaker':'Leo','quote':'The venue will be the North Hall.'}],
        [{'topic':'exhibition budget','value':'$9,500','speaker':'Mira','quote':'We must revise the exhibition budget to $9,500.'}],
        [{'topic':'venue','value':'North Hall','speaker':'Leo','quote':'We confirm that the venue remains the North Hall.'}],
    ][i]
    tasks = ([{'title':'Book the hall','description':'','owner':'Mira','deadline':'2027-04-08','priority':'high','quote':'I will book the hall by April 8, 2027.'}, {'title':'Prepare safety plan','description':'','owner':None,'deadline':None,'priority':'medium','quote':'We need a safety plan.'}] if i == 0 else [])
    return {'summary':'Exhibition planning','key_points':[],'follow_ups':[],'speakers':['Mira','Leo'],'decisions':decisions,'tasks':tasks,'completed':[]}

def fake(prompt, schema=None):
    if schema is A.EXTRACT_SCHEMA:
        return extraction(next(i for i, t in enumerate(TRANSCRIPTS) if t in prompt))
    if schema is A.COMPARE_SCHEMA:
        if '$9,500' in prompt:
            return {'pairs':[{'new_id':'new_0','old_id':1,'classification':'updates','explanation':'The budget changed.'}]}
        return {'pairs':[{'new_id':'new_0','old_id':2,'classification':'duplicate','explanation':'Same venue.'}]}
    return 'Your exhibition tasks and decisions are ready for review.'

class UserWorkflow(unittest.TestCase):
    def test_end_to_end(self):
        c = A.app.test_client()
        account = {'organization':'Exhibition','organization_code':'exhibition-secret-code','email':'admin@example.com','name':'Admin','password':'password-at-least-12','designation':'admin','create_organization':True}
        self.assertEqual(c.post('/api/auth/register',json=account).status_code,201)
        self.assertEqual(c.post('/api/auth/login',json=account).status_code,200)
        with patch.object(A, 'gemini', side_effect=fake):
            ids = []
            for i, transcript in enumerate(TRANSCRIPTS):
                body = {'title':f'Exhibition {i+1}', 'date':f'2027-04-0{i+1}', 'transcript':transcript}
                r = c.post('/api/meetings', json=body); self.assertEqual(r.status_code,201)
                ids.append(r.json['id'])
                self.assertEqual(c.post('/api/meetings',json=body).status_code,409)
                r = c.post(f'/api/meetings/{ids[-1]}/process'); self.assertEqual(r.status_code,200, r.json)
                self.assertEqual(r.json['source'], 'gemini')
            decisions = c.get('/api/decisions').json
            self.assertEqual(len(decisions),4)
            self.assertEqual(next(d for d in decisions if d['value']=='$9,500')['status'],'pending')
            self.assertEqual(next(d for d in decisions if d['meeting_id']==ids[2])['status'],'duplicate')
            conflict = c.get('/api/conflicts').json[0]
            self.assertEqual((conflict['old']['speaker'],conflict['new']['speaker']),('Mira','Mira'))
            self.assertEqual(conflict['old']['quote'], 'We agree the exhibition budget is $8,000.')
            tasks = c.get('/api/tasks').json
            self.assertEqual(next(t for t in tasks if t['title']=='Book the hall')['deadline'],'2027-04-08')
            self.assertEqual(next(t for t in tasks if t['title']=='Prepare safety plan')['owner'],A.UNCLEAR)
            tid = tasks[0]['id']
            self.assertEqual(c.post(f'/api/tasks/{tid}/sync').status_code,403)
            self.assertEqual(c.put(f'/api/tasks/{tid}',json={'owner':'Leo'}).status_code,200)
            self.assertEqual(len(c.get(f'/api/tasks/{tid}/history').json),2)
            self.assertEqual(c.post(f'/api/tasks/{tid}/approve',json={'approved':True}).status_code,200)
            class Response:
                status_code = 201
                def json(self): return {'html_url':'https://github.com/example/project/issues/1', 'number':1}
            with patch.object(A, 'gh_cfg', return_value={'token':'fake','owner':'example','repo':'project'}), patch.object(A.requests, 'post', return_value=Response()) as send:
                self.assertEqual(c.post(f'/api/tasks/{tid}/sync').status_code,200)
                self.assertEqual(c.post(f'/api/tasks/{tid}/sync').status_code,409)
                self.assertEqual(send.call_count,1)
                other=tasks[1]['id']
                c.post(f'/api/tasks/{other}/approve',json={'approved':True})
                send.side_effect=A.requests.Timeout('timeout')
                self.assertEqual(c.post(f'/api/tasks/{other}/sync').json['code'],'github_uncertain')
                self.assertEqual(c.post(f'/api/tasks/{other}/sync').status_code,409)
            self.assertEqual(c.get('/api/digest/Leo').json['source'],'gemini')
            self.assertEqual(c.post(f"/api/conflicts/{conflict['id']}/resolve",json={'action':'supersede'}).status_code,200)
            ds = c.get('/api/decisions').json
            self.assertEqual(next(d for d in ds if d['value']=='$8,000')['status'],'superseded')
            self.assertEqual(next(d for d in ds if d['value']=='$9,500')['status'],'active')
            self.assertEqual(c.post(f'/api/meetings/{ids[0]}/process').status_code,409)
            self.assertEqual(c.post('/api/demo/reset',headers={'Origin':'https://untrusted.example'}).status_code,403)
        env = dict(os.environ)
        code = 'import app; c=app.app.test_client(); c.post("/api/auth/login",json={"organization":"Exhibition","email":"admin@example.com","password":"password-at-least-12"}); print(len(c.get("/api/meetings").json),len(c.get("/api/conflicts").json))'
        result = subprocess.check_output([sys.executable,'-c',code],env=env,text=True).strip()
        self.assertEqual(result,'3 1')

if __name__ == '__main__':
    try: unittest.main()
    finally:
        if os.path.exists(path): os.remove(path)
        __import__('shutil').rmtree(path + '-orgs', ignore_errors=True)
