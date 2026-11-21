import os, tempfile, unittest, hashlib, sqlite3
from pathlib import Path
from unittest.mock import patch

TMP = tempfile.TemporaryDirectory()
os.environ['DATABASE_PATH'] = str(Path(TMP.name)/'legacy.db')
os.environ['ORGANIZATION_DATA_DIR'] = str(Path(TMP.name)/'organizations')
os.environ['AUTH_DATABASE_PATH'] = str(Path(TMP.name)/'accounts.db')
os.environ['GEMINI_API_KEY'] = ''
os.environ['SESSION_SECRET'] = 'sandbox-test-secret'
import app as A

class DemoIsolation(unittest.TestCase):
 def test_demo_entry_roles(self):
  for role,persona in [('employee','Sarah'),('manager','Alex'),('admin','Morgan')]:
   client=A.app.test_client()
   r=client.post('/api/auth/demo',json={'name':'Taylor','role':role})
   self.assertEqual(r.status_code,201,r.json)
   self.assertEqual((r.json['user']['role'],r.json['user']['name'],r.json['user']['demo_persona']),(role,'Taylor',persona))
   self.assertEqual(client.get('/api/auth/me').json['user']['role'],role)
   self.assertEqual(client.post('/api/auth/logout').status_code,200)

 def test_sandbox_and_permissions(self):
  a,b,anonymous=A.app.test_client(),A.app.test_client(),A.app.test_client()
  original=Path(os.environ['ORGANIZATION_DATA_DIR'])/'legacy-demo.db'
  before=hashlib.sha256(original.read_bytes()).hexdigest()
  self.assertEqual(a.post('/api/auth/demo',json={'name':'  '}).status_code,400)
  self.assertEqual(a.post('/api/auth/demo',json={'name':'x'*81}).status_code,400)
  self.assertEqual(a.post('/api/auth/demo',json={'name':'Casey','role':'unknown'}).status_code,400)
  self.assertEqual(a.post('/api/auth/demo',json={'name':'Casey'}).status_code,400)
  ra=a.post('/api/auth/demo',json={'name':'  Casey  ','role':'admin'}); rb=b.post('/api/auth/demo',json={'name':'Jordan','role':'manager'})
  self.assertEqual((ra.status_code,rb.status_code),(201,201))
  self.assertNotEqual(ra.json['user']['organization_id'],rb.json['user']['organization_id'])
  self.assertTrue(ra.json['user']['is_demo'])
  self.assertEqual(ra.json['user']['name'],'Casey')
  self.assertEqual(rb.json['user']['name'],'Jordan')
  self.assertEqual(len(a.get('/api/meetings').json),3)

  self.assertTrue(all(m['source']=='demo-fallback' for m in a.get('/api/meetings').json))
  meetings=a.get('/api/meetings').json
  self.assertEqual([(m['title'],__import__('datetime').date.fromisoformat(m['date']).weekday()) for m in meetings], [('Monday Planning',0),('Wednesday Review',2),('Friday Execution Review',4)])
  self.assertEqual(len(a.get('/api/conflicts').json),1)
  conflict=a.get('/api/conflicts').json[0]
  self.assertTrue(conflict['old']['value'].startswith('December 10,'))
  self.assertTrue(conflict['new']['value'].startswith('December 15,'))
  self.assertIn(conflict['old']['value'],conflict['old']['quote'])
  self.assertIn(conflict['new']['value'],conflict['new']['quote'])
  tasks=a.get('/api/tasks').json
  self.assertTrue(any(t['owner']=='Sarah' and t['deadline'] and t['approval']=='approved' for t in tasks))
  self.assertTrue(any(t['owner']=='Alex' and t['deadline'] and t['approval']=='approved' for t in tasks))
  self.assertTrue(any(t['owner']=='Owner unclear' and 'checklist' in t['title'].lower() and t['approval']=='pending' for t in tasks))
  self.assertTrue(any(t['title']=='Review product documentation' and t['approval']=='pending' for t in tasks))
  self.assertEqual(len(a.get('/api/organization/members').json),3)
  for role in ('employee','manager','admin'):
   r=a.post('/api/demo/role',json={'role':role}); self.assertEqual(r.status_code,200); self.assertEqual(r.json['user']['role'],role)
   self.assertEqual(r.json['user']['name'],'Casey')
   self.assertEqual(a.get('/api/auth/me').json['user']['name'],'Casey')
   self.assertEqual(a.get('/api/auth/me').json['user']['role'],role)
  self.assertEqual(anonymous.post('/api/demo/role',json={'role':'admin'}).status_code,401)
  self.assertEqual(a.post('/api/organization/invitations',json={'email':'x@example.com'}).status_code,403)
  self.assertEqual(a.put('/api/integrations/github',json={'token':'x'}).status_code,403)
  self.assertEqual(a.post('/api/demo/reset').status_code,403)
  first=a.post('/api/meetings',json={'title':'Capacity planning','date':'2027-02-01','transcript':'Morgan: The exhibition capacity is 100 people.'})
  self.assertEqual(first.status_code,201,first.json)
  self.assertFalse(any(m['title']=='Capacity planning' for m in b.get('/api/meetings').json))
  def fake(prompt,schema=None):
   if schema is A.COMPARE_SCHEMA:
    return {'pairs':[{'new_id':'new_0','old_id':3,'classification':'updates','explanation':'Capacity increased.'}]}
   value='150' if '150 people' in prompt else '100'
   return {'summary':'Capacity','key_points':[],'follow_ups':[],'speakers':['Morgan'], 'decisions':[{'topic':'capacity','value':value,'speaker':'Morgan','quote':f'The exhibition capacity is {value} people.'}],'tasks':[],'completed':[]}
  with patch.object(A,'gemini',side_effect=fake):
   self.assertEqual(a.post(f"/api/meetings/{first.json['id']}/process").status_code,200)
   second=a.post('/api/meetings',json={'title':'Capacity review','date':'2027-02-02','transcript':'Morgan: The exhibition capacity is 150 people.'})
   self.assertEqual(a.post(f"/api/meetings/{second.json['id']}/process").status_code,200)
  self.assertTrue(any(c['old']['value']=='100' and c['new']['value']=='150' for c in a.get('/api/conflicts').json))
  self.assertEqual(len(b.get('/api/conflicts').json),1)
  self.assertTrue(a.get('/api/reminders').json['upcoming'])
  self.assertEqual(a.post('/api/demo/role',json={'role':'manager'}).status_code,200)
  members=a.get('/api/organization/members').json
  sarah=next(m for m in members if m['name']=='Sarah')
  pending=next(t for t in a.get('/api/tasks').json if t['approval']=='pending')
  self.assertEqual(a.put(f"/api/tasks/{pending['id']}",json={'assignee_user_id':sarah['id']}).status_code,200)
  self.assertEqual(a.post(f"/api/tasks/{pending['id']}/approve",json={'approved':True}).status_code,200)
  self.assertEqual(a.post('/api/demo/role',json={'role':'employee'}).status_code,200)
  self.assertEqual(a.get('/api/people').json,['Sarah'])
  self.assertEqual(a.get('/api/auth/me').json['user']['demo_persona'],'Sarah')
  self.assertIn(pending['id'],[t['id'] for t in a.get('/api/tasks').json])
  self.assertEqual(a.post('/api/organization/departments',json={'name':'Unauthorized'}).status_code,403)
  self.assertEqual(a.post('/api/demo/sandbox/reset').status_code,200)
  self.assertEqual(a.get('/api/auth/me').json['user']['name'],'Casey')
  self.assertEqual(len(a.get('/api/meetings').json),3)
  self.assertEqual(len(b.get('/api/meetings').json),3)
  self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),before)
  self.assertEqual(b.post('/api/auth/logout').status_code,200)
  self.assertEqual(b.get('/api/meetings').status_code,401)
  self.assertEqual(len(a.get('/api/meetings').json),3)

 def test_transient_gemini_retry(self):
  class Response:
   def __init__(self,status): self.status_code=status; self.text='temporary error'
   def json(self): return {'candidates':[{'content':{'parts':[{'text':'ready'}]}}]}
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-key'}), patch.object(A.requests,'post',side_effect=[Response(503),Response(200)]) as post, patch.object(A.time,'sleep'):
   self.assertEqual(A.gemini('test'),'ready')
   self.assertEqual(post.call_count,2)

if __name__=='__main__': unittest.main()
