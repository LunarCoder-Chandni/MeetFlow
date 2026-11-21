import os, sys, tempfile, unittest, subprocess
from unittest.mock import patch
from pathlib import Path
import sqlite3

TMP = tempfile.TemporaryDirectory()
os.environ['DATABASE_PATH'] = str(Path(TMP.name) / 'legacy.db')
os.environ['ORGANIZATION_DATA_DIR'] = str(Path(TMP.name) / 'organizations')
os.environ['AUTH_DATABASE_PATH'] = str(Path(TMP.name) / 'accounts.db')
os.environ['GEMINI_API_KEY'] = ''
os.environ['SESSION_SECRET'] = 'test-only-secret-with-sufficient-length'
legacy = sqlite3.connect(os.environ['DATABASE_PATH'])
legacy.execute('CREATE TABLE meetings(id INTEGER PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL, transcript TEXT NOT NULL, summary TEXT, key_points TEXT, follow_ups TEXT, speakers TEXT, processed INTEGER DEFAULT 0, source TEXT, demo_key TEXT UNIQUE, created_at TEXT)')
legacy.execute("INSERT INTO meetings(title,date,transcript,demo_key,created_at) VALUES('Legacy Demo Meeting','2026-01-01','Speaker: Hello.','legacy','2026-01-01')")
legacy.commit(); legacy.close()
import app as A

class RoleTests(unittest.TestCase):
 def test_organization_workflow(self):
  admin, employee, manager, outsider = (A.app.test_client() for _ in range(4))
  def register(c, org, email, name, designation='employee', create=False, code=''):
   return c.post('/api/auth/register',json={'organization':org,'invitation_code':code,'email':email,'name':name,'password':'long-password-123','designation':designation,'create_organization':create})
  def login(c,org,email): return c.post('/api/auth/login',json={'organization':org,'email':email,'password':'long-password-123'})
  self.assertEqual(employee.get('/api/tasks').status_code,401)
  self.assertEqual(register(admin,'Acme','admin@example.com','Ava','admin',True).status_code,201)
  self.assertEqual(login(admin,'Acme','admin@example.com').json['user']['role'],'admin')
  self.assertEqual(admin.post('/api/demo/role',json={'role':'admin'}).status_code,403)
  with patch.dict(os.environ,{'GITHUB_TOKEN':'server-secret','GITHUB_OWNER':'server-owner','GITHUB_REPO':'server-repo','GITHUB_ENV_ORGANIZATION_ID':''},clear=False):
   self.assertFalse(admin.get('/api/integrations').json['github']['configured'])
  invitation=admin.post('/api/organization/invitations',json={'email':'employee@example.com','role':'employee'}).json['invitation_code']
  self.assertEqual(register(employee,'Acme','employee@example.com','Eva',code=invitation).status_code,201)
  self.assertEqual(register(outsider,'Acme','employee@example.com','Another',code=invitation).status_code,403)
  invite_manager=admin.post('/api/organization/invitations',json={'email':'manager@example.com','role':'manager'}).json['invitation_code']
  self.assertEqual(register(outsider,'Acme','wrong@example.com','Wrong',code=invite_manager).status_code,403)
  r=register(manager,'Acme','manager@example.com','Mina','manager',code=invite_manager); self.assertTrue(r.json['manager_approval_pending'])
  self.assertEqual(register(outsider,'Acme','evil@example.com','Mallory','admin').status_code,403)
  self.assertEqual(login(employee,'Acme','employee@example.com').json['user']['role'],'employee')
  self.assertEqual(login(manager,'Acme','manager@example.com').json['user']['role'],'employee')
  self.assertEqual(manager.post('/api/organization/departments',json={'name':'Bad'}).status_code,403)
  dep=admin.post('/api/organization/departments',json={'name':'Design'}).json['id']
  members=admin.get('/api/organization/members').json
  ev=next(x for x in members if x['name']=='Eva'); mi=next(x for x in members if x['name']=='Mina')
  self.assertEqual(employee.put(f"/api/organization/members/{ev['id']}",json={'role':'admin'}).status_code,403)
  self.assertEqual(admin.put(f"/api/organization/members/{ev['id']}",json={'department_id':dep}).status_code,200)
  self.assertEqual(admin.put(f"/api/organization/members/{mi['id']}",json={'department_id':dep,'role':'manager'}).status_code,200)
  self.assertEqual(manager.get('/api/auth/me').json['user']['role'],'manager')
  self.assertEqual(manager.get('/api/organization/members').status_code,200)
  self.assertTrue({'Eva','Mina'}.issubset({u['name'] for u in manager.get('/api/organization/members').json}))
  r=manager.post('/api/tasks',json={'title':'Prepare exhibit','assignee_user_id':ev['id'],'deadline':'2027-04-08'}); self.assertEqual(r.status_code,201,r.json); tid=r.json['id']
  self.assertEqual(len(employee.get('/api/tasks').json),1)
  self.assertEqual(employee.put(f'/api/tasks/{tid}',json={'owner':'Mina'}).status_code,403)
  self.assertEqual(employee.put(f'/api/tasks/{tid}',json={'status':'done'}).status_code,200)
  self.assertEqual(manager.get('/api/dashboard/stats').json['completed_tasks'],1)
  other=admin.post('/api/tasks',json={'title':'Private task'}); self.assertEqual(other.status_code,201)
  self.assertEqual(employee.get(f"/api/tasks/{other.json['id']}/history").status_code,404)
  self.assertEqual(employee.get('/api/dashboard/stats').json['active_tasks'],0)
  meeting=manager.post('/api/meetings',json={'title':'Exhibition','date':'2027-04-01','transcript':'Mina: The budget is $8,000. Eva: I will prepare the safety plan.'}); self.assertEqual(meeting.status_code,201,meeting.json); mid=meeting.json['id']
  self.assertEqual(employee.get(f'/api/meetings/{mid}').status_code,404)
  self.assertEqual(manager.post(f'/api/meetings/{mid}/participants',json={'user_id':ev['id']}).status_code,200)
  self.assertEqual(employee.get(f'/api/meetings/{mid}').status_code,200)
  extraction={'summary':'Budget','key_points':[],'follow_ups':[],'speakers':['Mina','Eva'],'decisions':[{'topic':'Exhibition Budget','value':'$8,000','speaker':'Mina','quote':'The budget is $8,000.'}],'tasks':[{'title':'Prepare safety plan','description':'','owner':'Eva','deadline':None,'priority':'medium','quote':'I will prepare the safety plan.'}],'completed':[]}
  with patch.object(A,'gemini',return_value=extraction):
   r=manager.post(f'/api/meetings/{mid}/process'); self.assertEqual(r.status_code,200,r.json)
  pending=next(t for t in manager.get('/api/tasks').json if t['title']=='Prepare safety plan')
  self.assertEqual(pending['assignee_user_id'],ev['id'])
  self.assertNotIn(pending['id'],[t['id'] for t in employee.get('/api/tasks').json])
  self.assertEqual(manager.post(f"/api/tasks/{pending['id']}/approve",json={'approved':True}).status_code,200)
  self.assertIn(pending['id'],[t['id'] for t in employee.get('/api/tasks').json])
  self.assertEqual(len(employee.get('/api/decisions').json),1)
  changed=manager.post('/api/meetings',json={'title':'Budget update','date':'2027-04-02','transcript':'Mina: The budget is now $9,500.'}); self.assertEqual(changed.status_code,201); mid2=changed.json['id']
  self.assertEqual(manager.post(f'/api/meetings/{mid2}/participants',json={'user_id':ev['id']}).status_code,200)
  changed_extraction={'summary':'Budget revised','key_points':[],'follow_ups':[],'speakers':['Mina'],'decisions':[{'topic':'Exhibition Budget','value':'$9,500','speaker':'Mina','quote':'The budget is now $9,500.'}],'tasks':[],'completed':[]}
  def ai(prompt,schema=None):
   if schema is A.COMPARE_SCHEMA: return {'pairs':[{'new_id':'new_0','old_id':1,'classification':'updates','explanation':'Budget changed.'}]}
   return changed_extraction
  with patch.object(A,'gemini',side_effect=ai): self.assertEqual(manager.post(f'/api/meetings/{mid2}/process').status_code,200)
  self.assertEqual(len(manager.get('/api/conflicts').json),1)
  self.assertTrue(employee.get('/api/notifications').json)
  dep2=admin.post('/api/organization/departments',json={'name':'Finance'}).json['id']
  hidden=admin.post('/api/meetings',json={'title':'Private finance','date':'2027-04-01','transcript':'Confidential','department_id':dep2}); self.assertEqual(hidden.status_code,201)
  self.assertEqual(manager.get(f"/api/meetings/{hidden.json['id']}").status_code,404)
  self.assertEqual(len(manager.get('/api/meetings').json),2)
  self.assertEqual(employee.get('/api/digest/Mina').status_code,404)
  peer_invite=admin.post('/api/organization/invitations',json={'email':'peer@example.com','role':'employee'}).json['invitation_code']
  peer=A.app.test_client()
  self.assertEqual(register(peer,'Acme','peer@example.com','Pia',code=peer_invite).status_code,201)
  pia=next(x for x in admin.get('/api/organization/members').json if x['name']=='Pia')
  self.assertEqual(admin.put(f"/api/organization/members/{pia['id']}",json={'department_id':dep}).status_code,200)
  assigned=admin.post('/api/tasks',json={'title':'Prepare handout','department_id':dep,'assignee_user_id':ev['id']})
  self.assertEqual(assigned.status_code,201,assigned.json)
  private=admin.post('/api/tasks',json={'title':'Private peer task','department_id':dep,'assignee_user_id':pia['id']})
  self.assertEqual(private.status_code,201,private.json)
  self.assertIn(assigned.json['id'],[t['id'] for t in employee.get('/api/tasks').json])
  self.assertNotIn(private.json['id'],[t['id'] for t in employee.get('/api/tasks').json])
  self.assertIn(private.json['id'],[t['id'] for t in manager.get('/api/tasks').json])
  self.assertEqual(register(outsider,'Other','other@example.com','Omar','admin',True).status_code,201)
  self.assertEqual(login(outsider,'Other','other@example.com').status_code,200)
  self.assertEqual(outsider.get('/api/meetings').json,[])
  self.assertEqual(outsider.get('/api/decisions').json,[])
  self.assertEqual(outsider.get('/api/tasks').json,[])
  self.assertEqual(outsider.get(f'/api/meetings/{mid}').status_code,404)
  self.assertEqual(employee.post('/api/demo/reset').status_code,403)
  code='import app; c=app.app.test_client(); r=c.post("/api/auth/login",json={"organization":"Acme","email":"employee@example.com","password":"long-password-123"}); print(r.status_code,len(c.get("/api/tasks").json))'
  self.assertEqual(subprocess.check_output([sys.executable,'-c',code],env=os.environ.copy(),text=True).strip(),'200 3')
  old_cookie=employee.get_cookie('session').value
  self.assertEqual(employee.post('/api/auth/logout').status_code,200)
  employee.set_cookie('session',old_cookie)
  self.assertEqual(employee.get('/api/tasks').status_code,401)
  demo = A.app.test_client()
  claim = Path(os.environ['ORGANIZATION_DATA_DIR'], 'demo-claim-code.txt').read_text()
  body={'organization':'MeetFlow Demo','organization_code':claim,'email':'demo@example.com','name':'Demo Admin','password':'long-password-123','designation':'admin','claim_demo':True}
  self.assertEqual(demo.post('/api/auth/register',json=body).status_code,201)
  self.assertEqual(login(demo,'MeetFlow Demo','demo@example.com').status_code,200)
  self.assertEqual(demo.get('/api/meetings').json[0]['title'],'Legacy Demo Meeting')
  body['email']='otheradmin@example.com'
  self.assertEqual(outsider.post('/api/auth/register',json=body).status_code,403)

if __name__=='__main__': unittest.main()
