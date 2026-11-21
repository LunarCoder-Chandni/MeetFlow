import os, tempfile, unittest, datetime as dt
from pathlib import Path
from unittest.mock import patch

TMP=tempfile.TemporaryDirectory()
os.environ['DATABASE_PATH']=str(Path(TMP.name)/'legacy.db')
os.environ['ORGANIZATION_DATA_DIR']=str(Path(TMP.name)/'organizations')
os.environ['AUTH_DATABASE_PATH']=str(Path(TMP.name)/'accounts.db')
os.environ['GEMINI_API_KEY']=''
os.environ['SESSION_SECRET']='feature-test-secret'
import app as A

class FeatureChecks(unittest.TestCase):
 def setUp(self):
  self.c=A.app.test_client()
  self.org='Feature '+self._testMethodName
  self.account={'organization':self.org,'email':self._testMethodName+'@example.com','name':'Admin','password':'password-at-least-12','designation':'admin','create_organization':True}
  self.assertEqual(self.c.post('/api/auth/register',json=self.account).status_code,201)
  self.assertEqual(self.c.post('/api/auth/login',json=self.account).status_code,200)

 def test_ai_failure_never_falls_back(self):
  c=self.c
  body={'title':'New product meeting','date':'2026-11-21','transcript':'Mira: We agreed the budget is $800.'}
  m=c.post('/api/meetings',json=body).json
  with patch.object(A,'gemini',side_effect=A.AIError('Simulated provider failure')):
   r=c.post(f"/api/meetings/{m['id']}/process")
  self.assertEqual((r.status_code,r.json['code']),(502,'ai_error'))
  stored=c.get(f"/api/meetings/{m['id']}").json
  self.assertEqual((stored['processed'],stored['source']),(0,None))
  self.assertEqual(stored['decisions'],[])
  with patch.object(A,'gemini',side_effect=A.AIUnavailable('Key missing')):
   r=c.post(f"/api/meetings/{m['id']}/process")
  self.assertEqual((r.status_code,r.json['code']),(400,'ai_not_configured'))
  def extract(value):
   return {'summary':'Budget','key_points':[],'follow_ups':[],'speakers':['Mira'], 'decisions':[{'topic':'budget','value':value,'speaker':'Mira','quote':f'We agreed the budget is {value}.'}],'tasks':[],'completed':[]}
  with patch.object(A,'gemini',return_value=extract('$800')):
   self.assertEqual(c.post(f"/api/meetings/{m['id']}/process").status_code,200)
  changed=c.post('/api/meetings',json={'title':'Budget review','date':'2026-11-22','transcript':'Mira: We agreed the budget is $900.'}).json
  with patch.object(A,'gemini',side_effect=[extract('$900'),A.AIUnavailable('Key missing during comparison')]):
   r=c.post(f"/api/meetings/{changed['id']}/process")
  self.assertEqual((r.status_code,r.json['code']),(400,'ai_not_configured'))
  self.assertEqual(c.get(f"/api/meetings/{changed['id']}").json['processed'],0)
  self.assertEqual(len(c.get('/api/decisions').json),1)
  self.assertEqual(c.post('/api/demo/load?process=0').status_code,200)
  demo=next(x for x in c.get('/api/meetings').json if x['demo_key']=='monday')
  with patch.object(A,'gemini',side_effect=A.AIError('Invalid key')):
   r=c.post(f"/api/meetings/{demo['id']}/process")
  self.assertEqual((r.status_code,r.json['code']),(502,'ai_error'))
  self.assertEqual(c.get(f"/api/meetings/{demo['id']}").json['processed'],0)

 def test_gemini_error_explains_unavailability(self):
  class Response:
   status_code=503
   text='upstream failure'
  with patch.dict(os.environ,{'GEMINI_API_KEY':'fake'}), patch.object(A.requests,'post',return_value=Response()) as send, patch.object(A.time,'sleep'):
   with self.assertRaises(A.AIError) as error:
    A.gemini('test')
   self.assertIn('temporarily unavailable',str(error.exception))
   self.assertEqual(send.call_count,3)

 def test_reminders_status_and_digests(self):
  c=self.c; due=(dt.date.today()+dt.timedelta(days=3)).isoformat()
  t=c.post('/api/tasks',json={'title':'Finish design','owner':'Admin','deadline':due}).json
  self.assertIn(t['id'],[x['id'] for x in c.get('/api/reminders').json['upcoming']])
  self.assertEqual(c.post('/api/demo/advance-time',json={'days':2}).status_code,200)
  self.assertIn(t['id'],[x['id'] for x in c.get('/api/reminders').json['due_soon']])
  self.assertEqual(c.post('/api/demo/advance-time',json={'days':1}).status_code,200)
  self.assertIn(t['id'],[x['id'] for x in c.get('/api/reminders').json['due_today']])
  before=c.get('/api/dashboard/stats').json
  self.assertEqual(c.put(f"/api/tasks/{t['id']}",json={'status':'done'}).status_code,200)
  after=c.get('/api/dashboard/stats').json
  self.assertEqual(after['completed_tasks'],before['completed_tasks']+1)
  self.assertEqual(after['active_tasks'],before['active_tasks']-1)
  with patch.object(A,'gemini',return_value='Verified summary'):
   individual=c.get('/api/digest/Admin'); team=c.get('/api/team/digest')
  self.assertEqual((individual.status_code,individual.json['source']),(200,'gemini'))
  self.assertEqual((team.status_code,team.json['source']),(200,'gemini'))
  self.assertIn('week_start',team.json['data'])
  self.assertTrue(any(x['title']=='Finish design' for x in team.json['data']['tasks']))

 def test_github_approval_and_error(self):
  c=self.c; t=c.post('/api/tasks',json={'title':'Prepare issue'}).json
  c.post('/api/tasks/%d/approve'%t['id'],json={'approved':False})
  with patch.object(A,'gh_cfg',return_value={'token':'fake','owner':'fake','repo':'fake'}), patch.object(A.requests,'post') as send:
   self.assertEqual(c.post('/api/tasks/%d/sync'%t['id']).status_code,403)
   send.assert_not_called()
   c.post('/api/tasks/%d/approve'%t['id'],json={'approved':True})
   send.return_value.status_code=403; send.return_value.text='Denied'; send.return_value.json.return_value={'message':'Denied'}
   r=c.post('/api/tasks/%d/sync'%t['id'])
   self.assertEqual((r.status_code,r.json['code']),(502,'github_error'))
   self.assertEqual(next(x for x in c.get('/api/tasks').json if x['id']==t['id'])['sync_status'],'failed')
   send.return_value.json.side_effect=ValueError('not JSON')
   r=c.post('/api/tasks/%d/sync'%t['id'])
   self.assertEqual((r.status_code,r.json['code']),(502,'github_error'))
   self.assertIn('HTTP 403',r.json['error'])

if __name__=='__main__': unittest.main()
