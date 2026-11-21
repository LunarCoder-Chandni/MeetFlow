"""Optional live Gemini check for the recording guide; uses a temporary demo database."""
import datetime as dt
import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as root:
    os.environ['DATABASE_PATH'] = str(Path(root) / 'legacy.db')
    os.environ['ORGANIZATION_DATA_DIR'] = str(Path(root) / 'organizations')
    os.environ['AUTH_DATABASE_PATH'] = str(Path(root) / 'accounts.db')
    os.environ['SESSION_SECRET'] = 'video-test-only-secret'
    import app as A

    c = A.app.test_client()
    r = c.post('/api/auth/demo', json={'name': 'Video Tester', 'role': 'admin'})
    assert r.status_code == 201, r.json
    conflict = c.get('/api/conflicts').json[0]
    year = conflict['old']['value'].split()[-1]
    transcript = (f'Morgan: We agreed to prepare a customer onboarding guide for the product launch.\n'
                  f'Sarah: I will draft the onboarding guide by December 2, {year}.\n'
                  f'Alex: I will review the onboarding guide by December 4, {year}.')
    r = c.post('/api/meetings', json={'title': 'Customer Onboarding', 'date': dt.date.today().isoformat(), 'transcript': transcript})
    assert r.status_code == 201, r.json
    r = c.post(f"/api/meetings/{r.json['id']}/process")
    assert r.status_code == 200, r.json
    assert r.json['source'] == 'gemini', r.json
    assert r.json['decisions'], r.json
    assert {'Sarah', 'Alex'}.issubset({t['owner'] for t in r.json['tasks']}), r.json
    assert all(t['deadline'] for t in r.json['tasks'] if t['owner'] in {'Sarah', 'Alex'}), r.json
    preserved = next(x for x in c.get('/api/conflicts').json if x['id'] == conflict['id'])
    assert preserved['status'] == 'open' and preserved['old']['status'] == 'active', preserved
    print('Live recording transcript: Gemini analysis, decision, owners and deadlines verified.')
