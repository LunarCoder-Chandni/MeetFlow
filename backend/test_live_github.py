"""Explicitly create one labelled GitHub issue through MeetFlow's approval flow."""
import argparse, datetime as dt, os, secrets, sqlite3, tempfile
from pathlib import Path
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--organization-id', type=int, required=True)
    parser.add_argument('--create-issue', action='store_true', required=True,
                        help='Explicitly create one external GitHub issue')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    settings = dotenv_values(base / '.env')
    legacy = Path(settings.get('DATABASE_PATH') or base / 'meetflow.db').resolve()
    org_dir = Path(settings.get('ORGANIZATION_DATA_DIR') or legacy.parent / 'meetflow-organizations').resolve()
    registry_path = Path(settings.get('AUTH_DATABASE_PATH') or org_dir / 'accounts.db').resolve()
    with sqlite3.connect(registry_path) as registry:
        row = registry.execute('SELECT db_name,is_demo FROM organizations WHERE id=?', (args.organization_id,)).fetchone()
    if not row or row[1]:
        raise SystemExit('The selected real organization was not found.')
    org_db = (org_dir / row[0]).resolve()
    if org_db.parent != org_dir or not org_db.is_file():
        raise SystemExit('The organization database is unavailable.')
    with sqlite3.connect(org_db) as source:
        saved = dict(source.execute("SELECT key,value FROM settings WHERE key IN ('gh_token','gh_owner','gh_repo')"))
    env_org = (settings.get('GITHUB_ENV_ORGANIZATION_ID') or '').strip()
    allow_env = (str(args.organization_id) == env_org) if env_org else row[0] == 'legacy-demo.db'
    cfg = {k: saved.get('gh_' + k) or (settings.get('GITHUB_' + k.upper()) if allow_env else '') for k in ('token', 'owner', 'repo')}
    if not all(cfg.values()):
        raise SystemExit('The selected organization has no complete GitHub configuration.')

    with tempfile.TemporaryDirectory() as tmp:
        os.environ['DATABASE_PATH'] = str(Path(tmp) / 'legacy.db')
        os.environ['ORGANIZATION_DATA_DIR'] = str(Path(tmp) / 'orgs')
        os.environ['AUTH_DATABASE_PATH'] = str(Path(tmp) / 'accounts.db')
        os.environ['SESSION_SECRET'] = secrets.token_hex(32)
        import app as A
        client = A.app.test_client()
        account = {'organization': 'GitHub Integration Test', 'email': 'test@example.invalid', 'name': 'Test Admin',
                   'password': secrets.token_urlsafe(24), 'designation': 'admin', 'create_organization': True}
        r = client.post('/api/auth/register', json=account); assert r.status_code == 201, r.json
        r = client.post('/api/auth/login', json=account); assert r.status_code == 200, r.json
        r = client.put('/api/integrations/github', json=cfg); assert r.status_code == 200, r.json
        r = client.post('/api/integrations/github/test'); assert r.status_code == 200, r.json
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        r = client.post('/api/tasks', json={'title': '[MeetFlow test] GitHub issue creation',
                                           'description': f'Integration verification created at {stamp}.'})
        assert r.status_code == 201, r.json
        task_id = r.json['id']
        assert client.post(f'/api/tasks/{task_id}/approve', json={'approved': False}).status_code == 200
        assert client.post(f'/api/tasks/{task_id}/sync').status_code == 403
        assert client.post(f'/api/tasks/{task_id}/approve', json={'approved': True}).status_code == 200
        r = client.post(f'/api/tasks/{task_id}/sync')
        if r.status_code != 200:
            raise SystemExit(f'GitHub sync failed or outcome uncertain: {r.json.get("error", "unknown error")}')
        print('Created and verified test issue:', r.json['issue_url'])


if __name__ == '__main__':
    main()
