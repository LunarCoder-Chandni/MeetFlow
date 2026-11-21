import os, tempfile
fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
os.environ['DATABASE_PATH'] = path
os.environ['ORGANIZATION_DATA_DIR'] = path + '-orgs'
os.environ['AUTH_DATABASE_PATH'] = __import__('os').path.join(path + '-orgs', 'accounts.db')
import app as A
c=A.app.test_client()
account={'organization':'Exhibition Live','organization_code':'exhibition-secret-code','email':'admin@example.com','name':'Admin','password':'password-at-least-12','designation':'admin','create_organization':True}
assert c.post('/api/auth/register',json=account).status_code==201
assert c.post('/api/auth/login',json=account).status_code==200
transcripts = [
 ('Exhibition planning','2027-04-01','Mira: We agree the exhibition budget is $8,000. Leo: The venue will be North Hall. Mira: I will book North Hall by April 8, 2027. Leo: We need a safety plan, but nobody has volunteered to prepare it yet.'),
 ('Exhibition budget review','2027-04-02','Mira: We need to increase the exhibition budget from $8,000 to $9,500. Leo: Agreed, the exhibition budget is now $9,500.'),
 ('Exhibition venue confirmation','2027-04-03','Leo: We confirm our exhibition venue remains North Hall. Mira: Agreed.')]
try:
 for title,date,transcript in transcripts:
  r=c.post('/api/meetings',json={'title':title,'date':date,'transcript':transcript}); assert r.status_code==201,r.json
  r=c.post('/api/meetings/%d/process'%r.json['id']); print('PROCESS',title,r.status_code,r.json if r.status_code!=200 else {'source':r.json['source'],'decisions':r.json['decisions'],'tasks':r.json['tasks']},flush=True); assert r.status_code==200
 conflicts=c.get('/api/conflicts').json
 decisions=c.get('/api/decisions').json
 tasks=c.get('/api/tasks').json
 assert any('$8,000' in x['old']['value'] and '$9,500' in x['new']['value'] and x['status']=='open' for x in conflicts), conflicts
 assert any(d['status']=='duplicate' and 'North Hall' in d['value'] for d in decisions), decisions
 assert any(t['owner']=='Owner unclear' and 'safety' in t['title'].lower() for t in tasks), tasks
 assert any(t['owner']=='Mira' and t['deadline']=='2027-04-08' for t in tasks), tasks
 r=c.get('/api/reminders'); assert r.status_code==200 and any(t['deadline']=='2027-04-08' for t in r.json['upcoming']),r.json
 r=c.get('/api/digest/Mira'); assert r.status_code==200 and r.json['source']=='gemini' and r.json['summary'],r.json
 conflict=next(x for x in conflicts if '$9,500' in x['new']['value'])
 r=c.post('/api/conflicts/%d/resolve'%conflict['id'],json={'action':'supersede'}); assert r.status_code==200,r.json
 decisions=c.get('/api/decisions').json
 assert next(d for d in decisions if d['id']==conflict['old_decision_id'])['status']=='superseded'
 assert next(d for d in decisions if d['id']==conflict['new_decision_id'])['status']=='active'
 print('Live Gemini extraction, conflict, duplicate, tasks, reminders, digest and resolution verified.',flush=True)
finally:
 if os.path.exists(path): os.remove(path)
 __import__('shutil').rmtree(path + '-orgs',ignore_errors=True)
