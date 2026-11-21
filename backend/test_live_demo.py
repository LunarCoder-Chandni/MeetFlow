import os, tempfile, hashlib
from pathlib import Path

with tempfile.TemporaryDirectory() as root:
 os.environ['DATABASE_PATH']=str(Path(root)/'legacy.db')
 os.environ['ORGANIZATION_DATA_DIR']=str(Path(root)/'organizations')
 os.environ['AUTH_DATABASE_PATH']=str(Path(root)/'accounts.db')
 os.environ['SESSION_SECRET']='live-demo-test-secret'
 import app as A
 c=A.app.test_client(); other=A.app.test_client()
 original=Path(root)/'organizations'/'legacy-demo.db'
 digest=lambda: hashlib.sha256(original.read_bytes()).hexdigest()
 before=digest()
 r=c.post('/api/auth/demo',json={'name':'Demo Tester','role':'admin'}); assert r.status_code==201,r.json
 assert other.post('/api/auth/demo',json={'name':'Second Tester','role':'admin'}).status_code==201
 for role in ('employee','manager','admin'):
  r=c.post('/api/demo/role',json={'role':role}); assert r.status_code==200 and r.json['user']['role']==role,r.json
 assert c.get('/api/reminders').json['upcoming']
 tasks=c.get('/api/tasks').json
 assert any(t['owner']=='Sarah' and t['assignee_user_id'] is not None for t in tasks),tasks
 for title,date,transcript in [
  ('Budget Planning','2027-04-01','Morgan: We agreed that the exhibition budget is $8,000. Sarah: I will book the venue by April 8, 2027.'),
  ('Budget Review','2027-04-02','Morgan: We are changing the exhibition budget from $8,000 to $9,500. Alex: Agreed, the new budget is $9,500.')]:
  r=c.post('/api/meetings',json={'title':title,'date':date,'transcript':transcript}); assert r.status_code==201,r.json
  r=c.post('/api/meetings/%d/process'%r.json['id']); assert r.status_code==200,r.json
  assert r.json['source']=='gemini',r.json
  print('Processed with Gemini:',title,flush=True)
 conflicts=c.get('/api/conflicts').json
 assert any('8,000' in x['old']['value'] and '9,500' in x['new']['value'] for x in conflicts),conflicts
 r=c.get('/api/digest/Sarah'); assert r.status_code==200 and r.json['source']=='gemini' and r.json['summary'],r.json
 assert not any(x['title']=='Budget Planning' for x in other.get('/api/meetings').json)
 assert c.post('/api/demo/sandbox/reset').status_code==200
 assert len(c.get('/api/meetings').json)==3 and len(other.get('/api/meetings').json)==3
 assert digest()==before
 print('Verified demo roles, live conflict, separate sandboxes, reset and unchanged original.',flush=True)
