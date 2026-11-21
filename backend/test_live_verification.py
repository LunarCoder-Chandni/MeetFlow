"""Optional live verification; sends fictional transcripts to Gemini using a temporary workspace."""
import os, tempfile, datetime as dt
from pathlib import Path

with tempfile.TemporaryDirectory() as root:
 os.environ['DATABASE_PATH']=str(Path(root)/'legacy.db')
 os.environ['ORGANIZATION_DATA_DIR']=str(Path(root)/'organizations')
 os.environ['AUTH_DATABASE_PATH']=str(Path(root)/'accounts.db')
 os.environ['SESSION_SECRET']='live-verification-only'
 import app as A
 c=A.app.test_client()
 r=c.post('/api/auth/demo',json={'name':'Verification','role':'admin'}); assert r.status_code==201,r.json
 today=dt.date.today(); due1=(today+dt.timedelta(days=12)).isoformat(); due2=(today+dt.timedelta(days=14)).isoformat()
 transcripts=[
  ('Cedar Summit Planning',f'Morgan: We agreed the Cedar Summit workshop capacity is 80 attendees.\nSarah: I will reserve the Cedar Summit hall by {due1}.\nAlex: I will prepare the Cedar Summit accessibility plan by {due2}.'),
  ('Cedar Summit Review','Morgan: We agreed to increase the Cedar Summit workshop capacity from 80 to 120 attendees.\nAlex: Agreed, the capacity is now 120 attendees.')]
 ids=[]
 for title, transcript in transcripts:
  r=c.post('/api/meetings',json={'title':title,'date':today.isoformat(),'transcript':transcript}); assert r.status_code==201,r.json
  ids.append(r.json['id']); r=c.post('/api/meetings/%d/process'%ids[-1]); assert r.status_code==200,r.json
  result=r.json; assert result['source']=='gemini',result
  assert result['decisions'] and all(d['quote'] and d['quote'] in transcript for d in result['decisions']),result
  if len(ids)==1:
   tasks=result['tasks']; assert {'Sarah','Alex'}.issubset({t['owner'] for t in tasks}),tasks
   for owner,due in [('Sarah',due1),('Alex',due2)]:
    assert any(t['owner']==owner and t['deadline']==due and t['quote'] and t['quote'] in transcript for t in tasks),tasks
  print('Gemini processing verified:',title,flush=True)
 conflicts=c.get('/api/conflicts').json
 assert any(x['old']['meeting_id']==ids[0] and x['new']['meeting_id']==ids[1] and '80' in x['old']['value'] and '120' in x['new']['value'] and x['old']['quote'] in transcripts[0][1] and x['new']['quote'] in transcripts[1][1] for x in conflicts),conflicts
 print('Cross-meeting conflict and evidence verified.',flush=True)
 for path in ('digest/Sarah','team/digest'):
  r=c.get('/api/'+path); assert r.status_code==200 and r.json['source']=='gemini' and r.json['summary'],r.json
  print('Live Gemini digest verified:',path,flush=True)
