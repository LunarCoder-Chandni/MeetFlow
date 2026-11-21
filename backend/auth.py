"""Account registry and session authentication for MeetFlow."""
import datetime as dt
import os, re, secrets, sqlite3, hashlib
from functools import wraps
from flask import request, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash

REGISTRY_SCHEMA = '''
CREATE TABLE IF NOT EXISTS organizations(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE, join_hash TEXT NOT NULL, db_name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS departments(id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id), name TEXT NOT NULL, UNIQUE(organization_id,name));
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id), department_id INTEGER REFERENCES departments(id), name TEXT NOT NULL, email TEXT NOT NULL COLLATE NOCASE, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('employee','manager','admin')), manager_requested INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, UNIQUE(organization_id,email));
CREATE TABLE IF NOT EXISTS login_attempts(key TEXT PRIMARY KEY, count INTEGER NOT NULL, last_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS user_sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS invitations(id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id), email TEXT NOT NULL COLLATE NOCASE, requested_role TEXT NOT NULL CHECK(requested_role IN ('employee','manager')), token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL, used_at TEXT, created_by INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS demo_sessions(token_hash TEXT PRIMARY KEY REFERENCES user_sessions(token_hash) ON DELETE CASCADE, organization_id INTEGER NOT NULL REFERENCES organizations(id), admin_id INTEGER NOT NULL REFERENCES users(id), manager_id INTEGER NOT NULL REFERENCES users(id), employee_id INTEGER NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL, ai_requests INTEGER NOT NULL DEFAULT 0);
'''


def configure(app, registry_path, org_dir, initialize_org, legacy_db, seed_demo):
    os.makedirs(org_dir, exist_ok=True)
    conn = sqlite3.connect(registry_path)
    conn.executescript(REGISTRY_SCHEMA)
    if 'is_demo' not in {r[1] for r in conn.execute('PRAGMA table_info(organizations)')}:
        conn.execute('ALTER TABLE organizations ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0')
    if 'write_requests' not in {r[1] for r in conn.execute('PRAGMA table_info(demo_sessions)')}:
        conn.execute('ALTER TABLE demo_sessions ADD COLUMN write_requests INTEGER NOT NULL DEFAULT 0')
    conn.execute('BEGIN IMMEDIATE')
    # A one-time, local-only claim code protects the copied legacy workspace.
    if not conn.execute("SELECT id FROM organizations WHERE name='MeetFlow Demo'").fetchone():
        claim_path = os.path.join(org_dir, 'demo-claim-code.txt')
        code = secrets.token_urlsafe(24)
        try:
            fd = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f: f.write(code)
        except FileExistsError:
            with open(claim_path) as f: code = f.read().strip()
        demo_path = os.path.join(org_dir, 'legacy-demo.db')
        if not os.path.exists(demo_path):
            source = sqlite3.connect(legacy_db); target = sqlite3.connect(demo_path)
            source.backup(target); target.close(); source.close()
        initialize_org(demo_path)
        conn.execute('INSERT INTO organizations(name,join_hash,db_name,created_at) VALUES(?,?,?,?)',('MeetFlow Demo',generate_password_hash(code),'legacy-demo.db',dt.datetime.now().isoformat()))
    conn.commit(); conn.close()
    secret = os.getenv('SESSION_SECRET', '')
    if not secret:
        secret_path = os.path.join(org_dir, '.session-secret')
        if not os.path.exists(secret_path):
            try:
                fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as f: f.write(secrets.token_hex(32))
            except FileExistsError:
                pass
        with open(secret_path) as f: secret = f.read().strip()
    app.secret_key = secret
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', '').lower() == 'true', PERMANENT_SESSION_LIFETIME=dt.timedelta(hours=12))

    def registry():
        if 'registry' not in g:
            g.registry = sqlite3.connect(registry_path, timeout=30)
            g.registry.row_factory = sqlite3.Row
            g.registry.execute('PRAGMA foreign_keys=ON')
        return g.registry
    def one(sql, *args):
        row = registry().execute(sql, args).fetchone()
        return dict(row) if row else None
    def public(u):
        result = {k:u[k] for k in ('id','name','email','role','department_id','manager_requested','organization_id','organization_name')}
        result['is_demo'] = bool(u['is_demo'])
        if result['is_demo']:
            result['organization_name'] = 'Demo Workspace'
            result['demo_persona'] = result['name']
            result['name'] = session.get('demo_name') or result['name']
        return result
    def fail(message, status=400): return jsonify(error=message), status
    def auth_required():
        return fail('Please sign in.', 401)
    def authenticated_user():
        uid, sid = session.get('uid'), session.get('sid')
        if not uid or not isinstance(sid,str): return None
        digest = hashlib.sha256(sid.encode()).hexdigest()
        return one('SELECT u.*,o.name organization_name,o.db_name,o.is_demo FROM user_sessions s JOIN users u ON u.id=s.user_id JOIN organizations o ON o.id=u.organization_id WHERE s.token_hash=? AND u.id=? AND u.active=1 AND s.expires_at>?',digest,uid,dt.datetime.now(dt.timezone.utc).isoformat())
    @app.teardown_appcontext
    def close_registry(exc):
        c = g.pop('registry', None)
        if c: c.close()
    @app.before_request
    def authenticate():
        if not request.path.startswith('/api/') or request.path.startswith('/api/auth/') or request.path == '/api/health': return None
        u = authenticated_user()
        if not u: return auth_required()
        g.user = u
        g.org_db_path = os.path.join(org_dir, u['db_name'])
        # These operations are privileged even if a caller bypasses the UI.
        ep = request.endpoint or ''
        if u['is_demo'] and ep in {'sync_task','save_github','test_github','load_demo','reset_all'}:
            return fail('External integrations are disabled in demo mode.', 403)
        if u['is_demo'] and request.method in ('POST','PUT','PATCH','DELETE'):
            token_hash = hashlib.sha256(session['sid'].encode()).hexdigest()
            c = registry()
            changed = c.execute('UPDATE demo_sessions SET write_requests=write_requests+1 WHERE token_hash=? AND write_requests<250 AND expires_at>?',(token_hash,dt.datetime.now(dt.timezone.utc).isoformat()))
            c.commit()
            if changed.rowcount != 1: return fail('This demo session has reached its change limit.',429)
        if u['is_demo'] and (ep == 'process' or ep in {'digest','team_digest'}):
            token_hash = hashlib.sha256(session['sid'].encode()).hexdigest()
            c = registry()
            changed = c.execute('UPDATE demo_sessions SET ai_requests=ai_requests+1 WHERE token_hash=? AND ai_requests<12 AND expires_at>?',(token_hash,dt.datetime.now(dt.timezone.utc).isoformat()))
            c.commit()
            if changed.rowcount != 1: return fail('This demo session has reached its AI request limit.', 429)
        admin_only = {'integrations','save_github','test_github','load_demo','reset_all','advance_time'}
        manager_only = {'resolve_conflict','approve_task','sync_task'}
        if ep in admin_only and u['role'] != 'admin': return fail('Administrator access required.', 403)
        if ep in manager_only and u['role'] not in ('admin','manager'): return fail('Manager access required.', 403)
        if ep == 'create_task' and u['role'] == 'employee': return fail('Manager access required.', 403)
        return None

    @app.post('/api/auth/register')
    def register():
        d = request.get_json(silent=True) or {}
        name = str(d.get('name','')).strip(); email = str(d.get('email','')).strip().lower()
        password = d.get('password',''); org = str(d.get('organization','')).strip()
        code = d.get('organization_code',''); invitation = d.get('invitation_code',''); requested = d.get('designation','employee')
        create = d.get('create_organization') is True
        if not (2 <= len(name) <= 100 and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) and len(email)<=254 and isinstance(password,str) and 12<=len(password)<=256 and 2<=len(org)<=100):
            return fail('Provide a name, valid email, organization, and password of at least 12 characters.')
        if requested not in ('employee','manager','admin'): return fail('Invalid designation.')
        c = registry()
        try:
            c.execute('BEGIN IMMEDIATE')
            o = one('SELECT * FROM organizations WHERE name=?',org)
            if create:
                if o: c.rollback(); return fail('Organization already exists.',409)
                if requested != 'admin': c.rollback(); return fail('The creator of a new organization must be its administrator.')
                filename = secrets.token_hex(16)+'.db'
                oid = c.execute('INSERT INTO organizations(name,join_hash,db_name,created_at) VALUES(?,?,?,?)',(org,generate_password_hash(secrets.token_urlsafe(32)),filename,dt.datetime.now().isoformat())).lastrowid
                initialize_org(os.path.join(org_dir,filename))
                role, manager_requested = 'admin',0
            else:
                if not o or o['is_demo']: c.rollback(); return fail('Invalid or expired invitation.',403)
                legacy_claim = o['name'] == 'MeetFlow Demo' and d.get('claim_demo') is True and requested == 'admin' and isinstance(code,str) and check_password_hash(o['join_hash'],code) and not one('SELECT id FROM users WHERE organization_id=?',o['id'])
                if legacy_claim:
                    role, manager_requested = 'admin', 0
                else:
                    if requested == 'admin' or not isinstance(invitation,str): c.rollback(); return fail('Invalid or expired invitation.',403)
                    inv = one('SELECT * FROM invitations WHERE token_hash=? AND organization_id=? AND lower(email)=? AND used_at IS NULL AND expires_at>?',hashlib.sha256(invitation.encode()).hexdigest(),o['id'],email,dt.datetime.now(dt.timezone.utc).isoformat())
                    if not inv: c.rollback(); return fail('Invalid or expired invitation.',403)
                    role, manager_requested = 'employee', int(inv['requested_role']=='manager' or requested=='manager')
                    c.execute('UPDATE invitations SET used_at=? WHERE id=? AND used_at IS NULL',(dt.datetime.now(dt.timezone.utc).isoformat(),inv['id']))
                oid=o['id']
            c.execute('INSERT INTO users(organization_id,name,email,password_hash,role,manager_requested,created_at) VALUES(?,?,?,?,?,?,?)',(oid,name,email,generate_password_hash(password),role,manager_requested,dt.datetime.now().isoformat()))
            c.commit()
        except sqlite3.IntegrityError:
            c.rollback(); return fail('This email is already registered in that organization.',409)
        return jsonify(message='Account created. Sign in to continue.', manager_approval_pending=bool(manager_requested)),201

    @app.post('/api/auth/login')
    def login():
        d=request.get_json(silent=True) or {}; email=str(d.get('email','')).strip().lower(); org=str(d.get('organization','')).strip(); password=d.get('password','')
        key=(request.remote_addr or '')+'|'+email[:254]+'|'+org[:100]
        c=registry(); a=one('SELECT * FROM login_attempts WHERE key=?',key); current=dt.datetime.now(dt.timezone.utc)
        if a and (current-dt.datetime.fromisoformat(a['last_at'])).total_seconds()<900 and a['count']>=8: return fail('Too many attempts. Try again later.',429)
        u=one('SELECT u.*,o.name organization_name,o.is_demo FROM users u JOIN organizations o ON o.id=u.organization_id WHERE u.email=? AND o.name=? AND u.active=1 AND o.is_demo=0',email,org)
        if not u or not isinstance(password,str) or not check_password_hash(u['password_hash'],password):
            count = (a['count']+1 if a and (current-dt.datetime.fromisoformat(a['last_at'])).total_seconds()<900 else 1)
            c.execute('INSERT INTO login_attempts(key,count,last_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET count=excluded.count,last_at=excluded.last_at',(key,count,current.isoformat())); c.commit()
            return fail('Invalid organization, email or password.',401)
        c.execute('DELETE FROM login_attempts WHERE key=?',(key,)); c.commit()
        sid=secrets.token_urlsafe(32)
        c.execute('INSERT INTO user_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(hashlib.sha256(sid.encode()).hexdigest(),u['id'],(current+dt.timedelta(hours=12)).isoformat())); c.commit()
        session.clear(); session['uid']=u['id']; session['sid']=sid; session.permanent=True
        return jsonify(user=public(u))

    @app.post('/api/auth/demo')
    def start_demo():
        data = request.get_json(silent=True) or {}
        supplied = data.get('name')
        if not isinstance(supplied,str) or not 1 <= len(supplied.strip()) <= 80 or re.search(r'[\x00-\x1f\x7f]',supplied):
            return fail('Enter your name (up to 80 characters) to explore the demo.')
        selected_role = data.get('role')
        if selected_role not in ('employee', 'manager', 'admin'):
            return fail('Choose a role to explore the demo.')
        display_name = supplied.strip()
        c = registry(); current = dt.datetime.now(dt.timezone.utc)
        limit_key = 'demo-start|' + (request.remote_addr or '')
        c.execute('BEGIN IMMEDIATE')
        attempt = one('SELECT * FROM login_attempts WHERE key=?',limit_key)
        count = attempt['count'] if attempt and (current-dt.datetime.fromisoformat(attempt['last_at'])).total_seconds()<3600 else 0
        if count >= 5:
            c.rollback(); return fail('Too many demo sessions started. Please try again later.',429)
        c.execute('INSERT INTO login_attempts(key,count,last_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET count=excluded.count,last_at=excluded.last_at',(limit_key,count+1,current.isoformat()))
        # Expired sandboxes are removed without touching the legacy demo or real organizations.
        expired = c.execute('SELECT d.token_hash,d.organization_id,o.db_name FROM demo_sessions d JOIN organizations o ON o.id=d.organization_id WHERE d.expires_at<? AND o.is_demo=1',(current.isoformat(),)).fetchall()
        for old in expired:
            c.execute('DELETE FROM demo_sessions WHERE token_hash=?',(old['token_hash'],))
            c.execute('DELETE FROM user_sessions WHERE token_hash=?',(old['token_hash'],))
            c.execute('DELETE FROM users WHERE organization_id=?',(old['organization_id'],))
            c.execute('DELETE FROM departments WHERE organization_id=?',(old['organization_id'],))
            c.execute('DELETE FROM organizations WHERE id=? AND is_demo=1',(old['organization_id'],))
            if re.fullmatch(r'demo-[0-9a-f]{32}\.db',old['db_name']):
                try: os.remove(os.path.join(org_dir,old['db_name']))
                except OSError: pass
        suffix = secrets.token_hex(16); filename = 'demo-'+suffix+'.db'
        oid = c.execute('INSERT INTO organizations(name,join_hash,db_name,created_at,is_demo) VALUES(?,?,?,?,1)',('Demo '+suffix, '!', filename, current.isoformat())).lastrowid
        department = c.execute('INSERT INTO departments(organization_id,name) VALUES(?,?)',(oid,'Product Team')).lastrowid
        ids = {}
        for role,name in [('admin','Morgan'),('manager','Alex'),('employee','Sarah')]:
            ids[role] = c.execute('INSERT INTO users(organization_id,department_id,name,email,password_hash,role,created_at) VALUES(?,?,?,?,?,?,?)',(oid,department,name,role+'@demo.invalid','!',role,current.isoformat())).lastrowid
        path = os.path.join(org_dir,filename)
        try:
            initialize_org(path); seed_demo(path,department,ids)
            sid=secrets.token_urlsafe(32); token_hash=hashlib.sha256(sid.encode()).hexdigest(); expires=(current+dt.timedelta(hours=12)).isoformat()
            c.execute('INSERT INTO user_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(token_hash,ids[selected_role],expires))
            c.execute('INSERT INTO demo_sessions(token_hash,organization_id,admin_id,manager_id,employee_id,expires_at) VALUES(?,?,?,?,?,?)',(token_hash,oid,ids['admin'],ids['manager'],ids['employee'],expires))
            c.commit()
        except Exception:
            c.rollback()
            try: os.remove(path)
            except OSError: pass
            raise
        session.clear(); session['uid']=ids[selected_role]; session['sid']=sid; session['demo_name']=display_name; session.permanent=True
        return jsonify(user=public(authenticated_user())),201

    @app.post('/api/demo/role')
    def demo_role():
        if not g.user['is_demo']: return fail('Role switching is available only in demo mode.',403)
        role = (request.get_json(silent=True) or {}).get('role')
        if role not in ('employee','manager','admin'): return fail('Invalid demo role.')
        digest=hashlib.sha256(session['sid'].encode()).hexdigest()
        d=one('SELECT * FROM demo_sessions WHERE token_hash=? AND organization_id=? AND expires_at>?',digest,g.user['organization_id'],dt.datetime.now(dt.timezone.utc).isoformat())
        if not d: return auth_required()
        uid=d[role+'_id']; c=registry(); c.execute('UPDATE user_sessions SET user_id=? WHERE token_hash=?',(uid,digest)); c.commit()
        session['uid']=uid
        return jsonify(user=public(authenticated_user()))

    @app.post('/api/demo/sandbox/reset')
    def reset_sandbox():
        if not g.user['is_demo']: return fail('This reset is available only in demo mode.',403)
        digest=hashlib.sha256(session['sid'].encode()).hexdigest()
        d=one('SELECT * FROM demo_sessions WHERE token_hash=? AND organization_id=? AND expires_at>?',digest,g.user['organization_id'],dt.datetime.now(dt.timezone.utc).isoformat())
        if not d: return auth_required()
        department=one('SELECT id FROM departments WHERE organization_id=? ORDER BY id LIMIT 1',g.user['organization_id'])
        if not department: return fail('Demo team is unavailable.',409)
        seed_demo(g.org_db_path,department['id'],{role:d[role+'_id'] for role in ('admin','manager','employee')})
        return jsonify(ok=True,message='Your demo sandbox has been reset.')

    @app.post('/api/organization/invitations')
    def create_invitation():
        if g.user['is_demo'] or g.user['role'] != 'admin': return fail('Administrator access required.',403)
        d=request.get_json(silent=True) or {}; email=str(d.get('email','')).strip().lower(); role=d.get('role','employee')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254 or role not in ('employee','manager'):
            return fail('Enter a valid email and invitation role.')
        token=secrets.token_urlsafe(32); expires=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=7)).isoformat(); c=registry()
        c.execute('INSERT INTO invitations(organization_id,email,requested_role,token_hash,expires_at,created_by) VALUES(?,?,?,?,?,?)',(g.user['organization_id'],email,role,hashlib.sha256(token.encode()).hexdigest(),expires,g.user['id'])); c.commit()
        return jsonify(invitation_code=token,email=email,expires_at=expires),201

    @app.post('/api/auth/logout')
    def logout():
        sid = session.get('sid')
        if isinstance(sid,str):
            c=registry(); token_hash=hashlib.sha256(sid.encode()).hexdigest()
            demo=one('SELECT d.organization_id,o.db_name FROM demo_sessions d JOIN organizations o ON o.id=d.organization_id WHERE d.token_hash=? AND o.is_demo=1',token_hash)
            if demo:
                c.execute('DELETE FROM demo_sessions WHERE token_hash=?',(token_hash,))
                c.execute('DELETE FROM user_sessions WHERE token_hash=?',(token_hash,))
                c.execute('DELETE FROM users WHERE organization_id=?',(demo['organization_id'],))
                c.execute('DELETE FROM departments WHERE organization_id=?',(demo['organization_id'],))
                c.execute('DELETE FROM organizations WHERE id=? AND is_demo=1',(demo['organization_id'],))
                c.commit()
                if re.fullmatch(r'demo-[0-9a-f]{32}\.db',demo['db_name']):
                    try: os.remove(os.path.join(org_dir,demo['db_name']))
                    except OSError: pass
            else:
                c.execute('DELETE FROM user_sessions WHERE token_hash=?',(token_hash,)); c.commit()
        session.clear(); return jsonify(ok=True)
    @app.get('/api/auth/me')
    def me():
        u=authenticated_user()
        return jsonify(user=public(u)) if u else auth_required()
    return registry
