import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import Galaxy from './components/Galaxy'
import MagicBento from './components/MagicBento'
import {
  LayoutDashboard, Mic, Brain, GitCompare, KanbanSquare, Bell, Newspaper, Plug, Settings as SettingsIcon,
  Check, Clock, Circle, Loader2, ExternalLink, AlertTriangle, Play, FastForward, RotateCcw, X, Plus, GitBranch, Sparkles, Users, UserRound, Building2, LogOut,
} from 'lucide-react'

const api = axios.create({ baseURL: '/api' })
const errMsg = (e) => e.response?.data?.error || (e.code === 'ERR_NETWORK' ? 'Cannot reach the backend on port 5001.' : e.message)
const human = (s = '') => s.replace(/_/g, ' ')
const fmt = (d) => (d ? new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'No deadline')

const NAV = [
  ['overview', 'Overview', LayoutDashboard], ['meetings', 'Meetings', Mic], ['decisions', 'Decision Memory', Brain],
  ['conflicts', 'Conflicts', GitCompare], ['tasks', 'Tasks', KanbanSquare], ['reminders', 'Reminders', Bell],
  ['digest', 'Weekly Digest', Newspaper], ['integrations', 'Integrations', Plug], ['settings', 'Settings', SettingsIcon],
]

const GALAXY_COLORS = ['#a79bff', '#7974c8', '#c4caff']
function AmbientGalaxy() {
  return <Galaxy className="app-galaxy" aria-hidden="true" starColors={GALAXY_COLORS} density={1.2} layers={3}
    glowIntensity={0.25} flareIntensity={0.35} twinkleIntensity={0.12} starSpeed={0.12} speed={0.55}
    rotationSpeed={0.015} mouseInteraction={false} mouseRepulsion={false} clickWarp={false} intro={false} dpr={1} />
}

function AuthScreen({ onLogin }) {
  const [register, setRegister] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', organization: '', organization_code: '', invitation_code: '', designation: 'employee', create_organization: false, claim_demo: false })
  const [demoName, setDemoName] = useState('')
  const [demoRole, setDemoRole] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
  const change = (key, value) => setForm((f) => ({ ...f, [key]: value }))
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError(''); setMessage('')
    try {
      if (register) {
        const r = await api.post('/auth/register', form)
        setMessage(r.data.manager_approval_pending ? 'Account created. Sign in as an employee while an admin reviews your manager request.' : 'Account created. Please sign in.')
        setRegister(false)
      } else onLogin((await api.post('/auth/login', form)).data.user)
    } catch (e) { setError(errMsg(e)) }
    setBusy(false)
  }
  return <div className="relative isolate grid min-h-screen place-items-center bg-ink-950 p-5"><AmbientGalaxy /><div className="card relative z-10 w-full max-w-lg space-y-5 p-7">
    <div><div className="flex items-center gap-2 text-sm font-semibold text-violet-300"><Sparkles size={18} /> MEETFLOW AI</div><h1 className="mt-4 text-2xl font-semibold text-white">{register ? 'Create your account' : 'Welcome back'}</h1><p className="mt-2 text-sm text-slate-400">Your organization’s intelligent execution layer.</p></div>
    <form className="space-y-3" onSubmit={submit}>
      {register && <input className="input" aria-label="Name" placeholder="Full name" value={form.name} onChange={(e) => change('name', e.target.value)} required />}
      <input className="input" aria-label="Organization name" placeholder="Organization name" value={form.organization} onChange={(e) => change('organization', e.target.value)} required />
      <input className="input" aria-label="Email" type="email" placeholder="Email" value={form.email} onChange={(e) => change('email', e.target.value)} required />
      <input className="input" aria-label="Password" type="password" placeholder={register ? 'Password (at least 12 characters)' : 'Password'} minLength={register ? 12 : undefined} value={form.password} onChange={(e) => change('password', e.target.value)} required />
      {register && <><label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={form.create_organization} onChange={(e) => setForm((f) => ({ ...f, create_organization: e.target.checked, claim_demo: false, designation: e.target.checked ? 'admin' : 'employee' }))} /> Create a new organization</label>
        {!form.create_organization && <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={form.claim_demo} onChange={(e) => setForm((f) => ({ ...f, claim_demo: e.target.checked, organization: e.target.checked ? 'MeetFlow Demo' : '', designation: e.target.checked ? 'admin' : 'employee' }))} /> Claim the existing demo workspace using its local claim code</label>}
        {!form.create_organization && (form.claim_demo ? <input className="input" aria-label="Legacy workspace claim code" type="password" placeholder="Legacy workspace claim code" value={form.organization_code} onChange={(e) => change('organization_code',e.target.value)} required /> : <input className="input" aria-label="Invitation code" type="password" placeholder="Invitation code from your administrator" value={form.invitation_code} onChange={(e) => change('invitation_code',e.target.value)} required />)}
        <fieldset><legend className="mb-2 text-sm text-slate-400">Choose your designation</legend><div className="grid gap-2">{[['employee','Employee','Personal meetings and assigned work'],['manager','Manager / Team Lead','Team work; requires admin approval'],['admin','Organization Admin','Create and manage an organization']].map(([v,label,sub]) => <button key={v} type="button" disabled={form.create_organization || form.claim_demo ? v !== 'admin' : v === 'admin'} onClick={() => change('designation',v)} className={`rounded-xl border p-3 text-left ${form.designation === v ? 'border-violet-500 bg-violet-950/30' : 'border-ink-600 bg-ink-800'} disabled:opacity-40`}><span className="block font-medium text-white">{label}</span><span className="text-xs text-slate-400">{sub}</span></button>)}</div></fieldset></>}
      {error && <p role="alert" className="text-sm text-red-300">{error}</p>}{message && <p role="status" className="text-sm text-emerald-300">{message}</p>}
      <button disabled={busy} className="btn-primary w-full justify-center">{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}</button>
    </form><button className="text-sm text-violet-300" onClick={() => { setRegister(!register); setError(''); setMessage('') }}>{register ? 'Already have an account? Sign in' : 'New here? Create an account'}</button>
    <form className="space-y-3 border-t border-ink-600/70 pt-4" onSubmit={async (e) => { e.preventDefault(); setBusy(true); setError(''); try { onLogin((await api.post('/auth/demo', { name: demoName.trim(), role: demoRole })).data.user) } catch (err) { setError(errMsg(err)); setBusy(false) } }}>
      <label htmlFor="demo-name" className="text-sm text-slate-300">Your name for the demo</label>
      <input id="demo-name" className="input" autoComplete="name" maxLength={80} placeholder="What should we call you?" value={demoName} onChange={(e) => setDemoName(e.target.value)} required />
      <fieldset><legend className="mb-2 text-sm text-slate-300">Choose a demo role</legend><div className="grid gap-2">{[['employee', 'Employee', 'Personal meetings and assigned tasks', UserRound], ['manager', 'Manager / Team Lead', 'Team meetings and task management', Users], ['admin', 'Organization Admin', 'Organization-wide overview and management', Building2]].map(([value, label, description, Icon]) => <label key={value} className={`flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-left transition-colors focus-within:outline focus-within:outline-2 focus-within:outline-violet-400 ${demoRole === value ? 'border-violet-500 bg-violet-950/30' : 'border-ink-600 bg-ink-800/70 hover:border-violet-500/50'}`}><input className="sr-only" type="radio" name="demo-role" value={value} checked={demoRole === value} onChange={() => setDemoRole(value)} required /><Icon size={18} className="shrink-0 text-violet-300" /><span><span className="block text-sm font-medium text-white">{label}</span><span className="block text-xs text-slate-400">{description}</span></span>{demoRole === value && <Check size={16} className="ml-auto shrink-0 text-violet-300" />}</label>)}</div></fieldset>
      <button disabled={busy || !demoName.trim() || !demoRole} className="btn-ghost w-full justify-center border border-violet-500/40 !py-3 text-violet-200"><Sparkles size={15} /> {busy ? 'Preparing workspace…' : 'Start demo'}</button><p className="text-center text-xs text-slate-500">No account needed · Your own resettable sandbox</p>
    </form>
  </div></div>
}

export default function App() {
  const [user, setUser] = useState(null), [loading, setLoading] = useState(true)
  useEffect(() => { api.get('/auth/me').then((r) => setUser(r.data.user)).catch(() => {}).finally(() => setLoading(false)) }, [])
  if (loading) return <div className="grid min-h-screen place-items-center"><Loader2 className="animate-spin" /></div>
  if (!user) return <AuthScreen onLogin={setUser} />
  return <Workspace key={`${user.organization_id}-${user.role}`} user={user} onLogout={() => setUser(null)} />
}

const TONE = {
  active: 'bg-emerald-950 text-emerald-300', superseded: 'bg-ink-700 text-slate-400', pending: 'bg-amber-950 text-amber-300',
  duplicate: 'bg-ink-700 text-slate-400', rejected: 'bg-red-950 text-red-300', open: 'bg-orange-950 text-orange-300',
  resolved: 'bg-emerald-950 text-emerald-300', high: 'bg-red-950 text-red-300', medium: 'bg-blue-950 text-blue-300',
  low: 'bg-ink-700 text-slate-300', gemini: 'bg-violet-950 text-violet-300', 'demo-fallback': 'bg-amber-950 text-amber-300',
  synced: 'bg-emerald-950 text-emerald-300', failed: 'bg-red-950 text-red-300', template: 'bg-amber-950 text-amber-300',
}
const Badge = ({ k, children }) => (
  <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${TONE[k] || 'bg-ink-700 text-slate-300'}`}>{children ?? k}</span>
)
const Empty = ({ children }) => <div className="card p-8 text-center text-sm text-slate-400">{children}</div>
const Title = ({ children, sub }) => (
  <div className="mb-5"><h1 className="text-xl font-semibold text-white">{children}</h1>{sub && <p className="mt-1 text-sm text-slate-400">{sub}</p>}</div>
)

function Workspace({ user, onLogout }) {
  const [page, setPage] = useState('overview')
  const [d, setD] = useState({ stats: null, meetings: [], tasks: [], conflicts: [], decisions: [], integ: null, health: null })
  const [down, setDown] = useState(false)
  const [toasts, setToasts] = useState([])
  const [notes, setNotes] = useState([])
  const [version, setVersion] = useState(0)

  const toast = (text, kind = 'ok') => {
    const id = Math.random()
    setToasts((t) => [...t, { id, text, kind }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000)
  }
  const nav = user.role === 'admin' ? [...NAV.filter(([k]) => !user.is_demo || k !== 'integrations'), ['departments', 'Departments', Building2], ['employees', 'Employees', Users], ['managers', 'Managers', Users], ['reports', 'Reports', LayoutDashboard], ['profile', 'Profile', UserRound]] : user.role === 'manager' ? [...NAV.filter(([k]) => !['integrations','settings'].includes(k)).map(([k,l,i]) => [k, k === 'meetings' ? 'Team Meetings' : k === 'tasks' ? 'Task Management' : l, i]), ['organization', 'Team Members', Users], ['profile', 'Profile', UserRound]] : [...NAV.filter(([k]) => !['conflicts','integrations','settings'].includes(k)).map(([k,l,i]) => [k, k === 'meetings' ? 'My Meetings' : k === 'tasks' ? 'My Tasks' : l, i]), ['profile', 'Profile', UserRound]]
  const refresh = useCallback(async () => {
    try {
      const [stats, meetings, tasks, conflicts, decisions, integ, health] = await Promise.all(
        ['/dashboard/stats', '/meetings', '/tasks', '/conflicts', '/decisions', ...(user.role === 'admin' ? ['/integrations'] : []), '/health'].map((u) => api.get(u).then((r) => r.data))).then((r) => user.role === 'admin' ? r : [...r.slice(0,5), null, r[5]])
      setD({ stats, meetings, tasks, conflicts, decisions, integ, health })
      setDown(false); setVersion((v) => v + 1)
    } catch { setDown(true) }
  }, [user.role])
  useEffect(() => { refresh() }, [refresh])

  const act = async (fn, ok) => {
    try { const r = await fn(); if (ok) toast(typeof ok === 'function' ? ok(r.data) : ok); await refresh(); return r.data } catch (e) { toast(errMsg(e), 'err') }
  }
  const advance = (body = { days: 2 }) => act(async () => {
    const r = await api.post('/demo/advance-time', body)
    setNotes(r.data.notifications); return r
  }, (x) => x.message)
  const ctx = { d, api, act, toast, refresh, advance, notes, setPage, version, user }
  const clock = d.stats?.clock

  return (
    <div className="relative isolate flex min-h-screen">
      <AmbientGalaxy />
      <aside className="relative z-10 hidden w-56 shrink-0 border-r border-ink-700 bg-ink-900 p-4 md:block">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-blue-600 to-violet-500"><Sparkles size={15} className="text-white" /></div>
          <span className="font-semibold text-white">MeetFlow AI</span>
        </div>
        <nav className="space-y-0.5">
          {nav.map(([k, label, Icon]) => (
            <button key={k} onClick={() => setPage(k)} aria-current={page === k}
              className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${page === k ? 'bg-ink-700 text-white' : 'text-slate-400 hover:bg-ink-800 hover:text-slate-200'}`}>
              <Icon size={16} /> {label}
              {k === 'conflicts' && d.stats?.open_conflicts > 0 && <span className="ml-auto rounded-full bg-orange-600 px-1.5 text-xs text-white">{d.stats.open_conflicts}</span>}
            </button>
          ))}
        </nav>
      </aside>

      <div className="relative z-10 min-w-0 flex-1">
        <header className="sticky top-0 z-10 flex flex-wrap items-center gap-3 border-b border-ink-700 bg-ink-950/90 px-5 py-3 backdrop-blur">
          <select className="input !w-auto md:hidden" value={page} onChange={(e) => setPage(e.target.value)} aria-label="Navigate">
            {nav.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          <p className="hidden text-sm text-slate-400 md:block">From conversations to commitments. Automatically.</p>
          <div className="ml-auto flex items-center gap-2">
            {clock && (clock.simulated
              ? <span className="rounded-lg border border-amber-700/60 bg-amber-950/60 px-2.5 py-1 text-xs text-amber-300">Simulated {fmt(clock.sim_date)} (real date {fmt(clock.real_date)})</span>
              : <span className="rounded-lg bg-ink-800 px-2.5 py-1 text-xs text-slate-400">Today {fmt(clock.real_date)}</span>)}
            <span className="max-w-[10rem] truncate text-xs text-slate-300 sm:max-w-xs" title={`${user.name} · ${user.role} · ${user.organization_name}`}>{user.name} · {user.role} · {user.organization_name}</span>
            <button className="btn-ghost" onClick={async () => { try { await api.post('/auth/logout'); onLogout() } catch (e) { toast(errMsg(e), 'err') } }}><LogOut size={14} /> Log out</button>
          </div>
        </header>

        {user.is_demo && <div className="flex flex-wrap items-center gap-3 border-b border-violet-500/30 bg-violet-950/40 px-5 py-3 text-sm"><span className="rounded-md bg-violet-500/25 px-2 py-1 text-xs font-bold tracking-wider text-violet-200">DEMO MODE</span><span className="text-xs text-slate-300">Your private sandbox · Previewing {user.demo_persona}'s data · Changes are temporary</span><button className="btn-ghost ml-auto" onClick={() => window.confirm('Reset your demo sandbox to its starting data?') && act(() => api.post('/demo/sandbox/reset'), 'Your demo sandbox was reset')}>Reset demo</button></div>}

        {down && <div className="m-5 flex items-center gap-2 rounded-lg border border-red-800 bg-red-950/60 p-3 text-sm text-red-300"><AlertTriangle size={16} /> The backend is not responding. Start it with <code>python app.py</code> in the backend folder, then reload.</div>}
        {d.health && !d.health.gemini_configured && (
          <div className="mx-5 mt-4 rounded-lg border border-amber-800/60 bg-amber-950/40 p-3 text-sm text-amber-200">
            Gemini API key not set. Demo transcripts run on a deterministic fallback and are labelled as demo data. Your own transcripts need <code>GEMINI_API_KEY</code> in <code>backend/.env</code>.
          </div>)}

        <main className="mx-auto max-w-6xl p-5">
          {page === 'overview' && <Overview {...ctx} />}
          {page === 'meetings' && <Meetings {...ctx} />}
          {page === 'decisions' && <Decisions {...ctx} />}
          {page === 'conflicts' && <Conflicts {...ctx} />}
          {page === 'tasks' && <Tasks {...ctx} />}
          {page === 'reminders' && <Reminders {...ctx} />}
          {page === 'digest' && <Digest {...ctx} />}
          {page === 'integrations' && <Integrations {...ctx} />}
          {page === 'settings' && <Settings {...ctx} />}
          {page === 'organization' && <Organization {...ctx} />}
          {['departments','employees','managers','reports'].includes(page) && <Organization {...ctx} section={page} />}
          {page === 'profile' && <div className="card p-5"><Title>Profile</Title><p>{user.name}</p><p className="text-slate-400">{user.email} · {user.role} · {user.organization_name}</p></div>}
        </main>
      </div>

      <div className="fixed bottom-4 right-4 z-20 space-y-2" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`max-w-sm rounded-lg border px-4 py-3 text-sm shadow-xl ${t.kind === 'err' ? 'border-red-800 bg-red-950 text-red-200' : 'border-ink-600 bg-ink-800 text-slate-100'}`}>{t.text}</div>))}
      </div>
    </div>
  )
}

/* ---------------- Overview ---------------- */
function Overview({ d, act, api, setPage, user, version }) {
  const s = d.stats
  const [alerts, setAlerts] = useState([])
  useEffect(() => { api.get('/notifications').then((r) => setAlerts(r.data)).catch(() => {}) }, [api, version])
  if (!s) return <Loader2 className="animate-spin text-slate-500" />
  const cells = [
    ['Meetings', s.meetings, Mic, 'meetings'], ['Decisions', s.decisions, Brain, 'decisions'],
    ['Active tasks', s.active_tasks, KanbanSquare, 'tasks'], ['Completed', s.completed_tasks, Check, 'tasks'],
    ['Open conflicts', s.open_conflicts, GitCompare, user.role === 'employee' ? null : 'conflicts', s.open_conflicts > 0 && 'text-orange-400'],
    ['Overdue', s.overdue_tasks, Clock, 'reminders', s.overdue_tasks > 0 && 'text-red-400'],
  ]
  const bentoItems = [
    ...cells.map(([label, value, Icon, destination, color]) => ({
      id: label,
      title: `${label}: ${value}${destination ? `. Open ${destination}` : ''}`,
      ...(destination ? { onClick: () => setPage(destination) } : {}),
      content: <div className="bento-stat"><div className="bento-stat-top"><span>{label}</span><span className="stat-icon"><Icon size={15} /></span></div><div className={`bento-stat-value ${color || ''}`}>{value}</div>{destination && <span className="bento-stat-link">View details <span aria-hidden="true">↗</span></span>}</div>,
    })),
    {
      id: 'activity', colSpan: 3, rowSpan: 2,
      content: <section className="bento-panel"><div className="bento-panel-heading"><div><p className="bento-eyebrow">YOUR WORKSPACE</p><h2>Recent activity</h2></div><span className="bento-panel-icon"><Circle size={15} /></span></div>
        {s.activity.length === 0 ? <p className="bento-empty">Nothing has happened yet.</p> : <ul className="bento-list" tabIndex={0} aria-label="Recent activity">{s.activity.map((a) => <li key={a.id} className="bento-activity"><span className="bento-dot" /> <span>{a.text}</span></li>)}</ul>}
      </section>,
    },
    {
      id: 'deadlines', colSpan: 3, rowSpan: 2,
      content: <section className="bento-panel"><div className="bento-panel-heading"><div><p className="bento-eyebrow">COMING UP</p><h2>Upcoming deadlines</h2></div><span className="bento-panel-icon"><Clock size={16} /></span></div>
        {s.upcoming.length === 0 ? <p className="bento-empty">No deadlines on the books.</p> : <ul className="bento-list" tabIndex={0} aria-label="Upcoming deadlines">{s.upcoming.map((t) => <li key={t.id} className="bento-deadline"><span className="min-w-0"><span className="block truncate text-slate-200">{t.title}</span><span className="text-xs text-slate-500">{t.owner}</span></span><span className="bento-date">{fmt(t.deadline)}</span></li>)}</ul>}
      </section>,
    },
  ]
  return (
    <>
      <div className="overview-welcome mb-6">
        <div className="relative z-10">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-violet-300/80">{user.role === 'admin' ? 'Organization overview' : user.role === 'manager' ? 'Team overview' : 'Your workspace'}</p>
          <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Hi, {user.name}</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-400">Everything your meetings committed to, in one place.</p>
        </div>
        <div className="welcome-sparkle" aria-hidden="true"><Sparkles size={24} /></div>
      </div>
      {s.meetings === 0 && (
        <div className="card mb-5 flex flex-wrap items-center justify-between gap-3 p-5">
          <p className="text-sm text-slate-300">No meetings yet. Add a transcript to start building decision memory.</p>
          <button className="btn-primary" onClick={() => setPage('meetings')}><Plus size={14} /> Add meeting</button>
        </div>)}
      {alerts.some((n) => !n.read_at) && <section className="card mb-5 p-4"><h2 className="mb-2 text-sm font-medium text-white">Notifications</h2>{alerts.filter((n) => !n.read_at).map((n) => <div key={n.id} className="flex items-center justify-between gap-3 py-1 text-sm text-slate-300"><span>{n.message}</span><button className="btn-ghost" onClick={() => act(() => api.post(`/notifications/${n.id}/read`), 'Notification marked read')}>Mark read</button></div>)}</section>}
      <MagicBento className="overview-bento" items={bentoItems} columns={6} rowHeight={146} gap={12} radius={18} glowColor="#a99bff" spotlightRadius={260} enableBorderGlow enableSpotlight clickEffect intro={false} />
    </>
  )
}

/* ---------------- Meetings ---------------- */
function Pipeline({ stages }) {
  const icon = { done: <Check size={13} />, waiting: <Clock size={13} />, pending: <Circle size={9} /> }
  const color = { done: 'bg-blue-600 text-white', waiting: 'bg-amber-500 text-black', pending: 'bg-ink-700 text-slate-500' }
  return (
    <ol className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {stages.map((s) => (
        <li key={s.name} className="text-xs">
          <div className="flex items-center gap-2"><span className={`grid h-5 w-5 place-items-center rounded-full ${color[s.status]}`}>{icon[s.status]}</span><span className="font-medium text-slate-200">{s.name}</span></div>
          <p className="mt-1 pl-7 text-slate-500">{s.detail}</p>
        </li>))}
    </ol>
  )
}

function Meetings({ d, act, api, version, toast, user }) {
  const [sel, setSel] = useState(null)
  const [m, setM] = useState(null)
  const [busy, setBusy] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ title: '', date: new Date().toISOString().slice(0, 10), transcript: '' })
  const [departments, setDepartments] = useState([]), [members, setMembers] = useState([]), [participant, setParticipant] = useState('')
  useEffect(() => { api.get('/organization/departments').then((r) => setDepartments(r.data)); if (user.role !== 'employee') api.get('/organization/members').then((r) => setMembers(r.data)) }, [api, user.role, version])
  useEffect(() => { if (!sel && d.meetings.length) setSel(d.meetings[d.meetings.length - 1].id) }, [d.meetings, sel])
  useEffect(() => { if (sel) api.get(`/meetings/${sel}`).then((r) => setM(r.data)).catch(() => setM(null)) }, [sel, version, api])

  const create = async () => {
    setSaving(true)
    const r = await act(() => api.post('/meetings', form), 'Meeting saved. Process it to extract decisions and tasks.')
    if (r) { setSel(r.id); setForm({ ...form, title: '', transcript: '' }) }
    setSaving(false)
  }
  const process = async () => {
    setBusy(true)
    await act(() => api.post(`/meetings/${m.id}/process`), (x) => `Processed: ${x.decisions.length} decisions, ${x.tasks.length} tasks`)
    setBusy(false)
  }
  return (
    <>
      <Title sub="Paste a transcript, then let the agent read it against everything it already remembers.">Meetings</Title>
      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <div className="space-y-4">
          <div className="card space-y-2.5 p-4">
            <h2 className="text-sm font-medium text-white">New meeting</h2>
            <p className="text-xs text-slate-400">Add speaker labels, save, then select Process with agent. Demo data is optional.</p>
            <input className="input" maxLength={200} aria-label="Meeting title" placeholder="Meeting title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <input className="input" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            {user.role === 'admin' && <select className="input" aria-label="Meeting department" value={form.department_id || ''} onChange={(e) => setForm({ ...form, department_id: e.target.value ? Number(e.target.value) : null })}><option value="">Organization-wide (admin only)</option>{departments.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>}
            <textarea className="input h-36" maxLength={100000} aria-label="Meeting transcript" placeholder={'Name: We agreed on the budget.\nName: I will prepare the plan by next Friday.'} value={form.transcript} onChange={(e) => setForm({ ...form, transcript: e.target.value })} />
            <button className="btn-primary w-full justify-center" disabled={saving || !form.title.trim() || !form.date || !form.transcript.trim()} onClick={create}>{saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} {saving ? 'Saving…' : 'Save meeting'}</button>
          </div>
          <div className="card divide-y divide-ink-700">
            {d.meetings.length === 0 && <p className="p-4 text-sm text-slate-500">No meetings saved yet.</p>}
            {d.meetings.map((x) => (
              <button key={x.id} onClick={() => setSel(x.id)} className={`block w-full p-3 text-left hover:bg-ink-800 ${sel === x.id ? 'bg-ink-800' : ''}`}>
                <div className="flex items-center justify-between gap-2 text-sm text-white"><span className="min-w-0 truncate" title={x.title}>{x.title}</span>{!x.processed && <span className="shrink-0"><Badge k="pending">Not processed</Badge></span>}</div>
                <div className="mt-0.5 text-xs text-slate-500">{fmt(x.date)} · {x.decisions} decisions · {x.tasks} tasks</div>
              </button>))}
          </div>
        </div>

        {!m ? <Empty>Select or save a meeting to see the agent’s work.</Empty> : (
          <div className="space-y-4">
            <div className="card p-4">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <h2 className="text-lg font-semibold text-white">{m.title}</h2><span className="text-sm text-slate-500">{fmt(m.date)}</span>
                {m.source && <Badge k={m.source}>{m.source === 'gemini' ? 'Gemini analysis' : 'Demo fallback data'}</Badge>}
                {!m.processed && <button className="btn-primary ml-auto" disabled={busy} onClick={process}>{busy ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} {busy ? 'Processing meeting…' : 'Process with agent'}</button>}
              </div>
              {busy && <p role="status" className="mb-4 text-sm text-violet-200">The agent is analyzing the transcript and checking decision memory. This can take a minute.</p>}
              <Pipeline stages={m.stages} />
              {user.role !== 'employee' && <div className="mt-4 flex flex-wrap gap-2"><select className="input !w-auto" aria-label="Meeting participant" value={participant} onChange={(e) => setParticipant(e.target.value)}><option value="">Select participant</option>{members.filter((x) => user.role === 'admin' || x.department_id === m.department_id).map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select><button className="btn-ghost" disabled={!participant} onClick={() => act(() => api.post(`/meetings/${m.id}/participants`, { user_id: Number(participant) }), 'Participant added')}>Add participant</button></div>}
            </div>
            {m.processed && (
              <div className="card space-y-4 p-4 text-sm">
                <p className="text-slate-200">{m.summary}</p>
                {m.speakers.length > 0 && <p className="text-slate-400">Speakers: {m.speakers.join(', ')}</p>}
                {m.key_points.length > 0 && <ul className="list-disc space-y-1 pl-5 text-slate-400">{m.key_points.map((k, i) => <li key={i}>{k}</li>)}</ul>}
                {m.follow_ups.length > 0 && <div className="rounded-lg bg-amber-950/40 p-3 text-amber-200">{m.follow_ups.map((f, i) => <p key={i}>{f}</p>)}</div>}
                <div><h3 className="mb-2 font-medium text-white">Decisions</h3>
                  {m.decisions.length === 0 ? <p className="text-slate-500">No decisions in this meeting.</p> : m.decisions.map((x) => (
                    <div key={x.id} className="mb-2 rounded-lg bg-ink-800 p-3"><div className="flex items-center gap-2"><span className="text-white">{human(x.topic)}: {x.value}</span><Badge k={x.status} /></div><p className="mt-1 text-slate-400">{x.speaker}: “{x.quote}”</p></div>))}
                </div>
                <div><h3 className="mb-2 font-medium text-white">Tasks</h3>
                  {m.tasks.length === 0 ? <p className="text-slate-500">No new tasks from this meeting.</p> : m.tasks.map((t) => (
                    <div key={t.id} className="mb-2 rounded-lg bg-ink-800 p-3"><div className="flex flex-wrap items-center gap-2"><span className="text-white">{t.title}</span><Badge k={t.priority} />
                      <span className={t.owner === 'Owner unclear' ? 'text-amber-300' : 'text-slate-400'}>{t.owner}</span><span className="text-slate-500">{fmt(t.deadline)}</span>
                      {t.status === 'done' && <Badge k="resolved">Done</Badge>}</div>{t.quote && <p className="mt-1 text-slate-500">“{t.quote}”</p>}</div>))}
                </div>
              </div>)}
            <details className="card p-4 text-sm"><summary className="cursor-pointer text-slate-300">Transcript</summary><pre className="mt-3 whitespace-pre-wrap font-sans text-slate-400">{m.transcript}</pre></details>
          </div>)}
      </div>
    </>
  )
}

/* ---------------- Decision memory ---------------- */
function Decisions({ d }) {
  const [query, setQuery] = useState('')
  const term = query.trim().toLowerCase()
  const filtered = d.decisions.filter((x) => [x.topic, human(x.topic), x.value, x.speaker, x.quote, x.meeting_title, x.status].some((v) => String(v || '').toLowerCase().includes(term)))
  const groups = filtered.reduce((a, x) => ((a[x.topic] ||= []).push(x), a), {})
  return (
    <>
      <Title sub="Every decision the agent has recorded. Superseded decisions stay in the history.">Decision Memory</Title>
      {d.decisions.length > 0 && <input className="input mb-4 max-w-md" type="search" aria-label="Search decision memory" placeholder="Search decisions, speakers, or meetings" value={query} onChange={(e) => setQuery(e.target.value)} />}
      {Object.keys(groups).length === 0 ? <Empty>{d.decisions.length ? 'No decisions match your search.' : 'No decisions recorded yet. Process a meeting to start building memory.'}</Empty> :
        <div className="space-y-4">{Object.entries(groups).map(([topic, items]) => (
          <section key={topic} className="card p-4"><h2 className="mb-3 font-medium capitalize text-white">{human(topic)}</h2>
            <ol className="space-y-3 border-l border-ink-600 pl-4">{items.map((x) => (
              <li key={x.id} className={x.status === 'superseded' || x.status === 'rejected' ? 'opacity-55' : ''}>
                <div className="flex flex-wrap items-center gap-2 text-sm"><span className={`font-medium text-slate-100 ${x.status === 'superseded' ? 'line-through' : ''}`}>{x.value}</span><Badge k={x.status} />
                  <span className="text-slate-500">{x.meeting_title}, {fmt(x.meeting_date)}</span></div>
                <p className="text-sm text-slate-400">{x.speaker}: “{x.quote}”</p></li>))}</ol>
          </section>))}</div>}
    </>
  )
}

/* ---------------- Conflicts ---------------- */
function Side({ label, x, tone }) {
  return (
    <div className={`rounded-lg border p-4 ${tone}`}>
      <div className="text-xs font-medium text-slate-400">{label}</div>
      <div className="mt-1 text-lg font-semibold text-white">{x.value}</div>
      <div className="mt-2 text-sm text-slate-400">{x.meeting_title}, {fmt(x.meeting_date)}</div>
      <div className="text-sm text-slate-400">Speaker: {x.speaker}</div>
      <p className="mt-2 text-sm text-slate-300">“{x.quote}”</p>
    </div>
  )
}
function Conflicts({ d, act, api }) {
  const resolve = (id, action, msg) => act(() => api.post(`/conflicts/${id}/resolve`, { action }), msg)
  return (
    <>
      <Title sub="The agent never overwrites a decision on its own. You choose which one stands.">Conflict Detection</Title>
      {d.conflicts.length === 0 ? <Empty>No conflicts. Conflicts appear when a new meeting changes something decided earlier.</Empty> :
        <div className="space-y-5">{d.conflicts.map((c) => (
          <section key={c.id} className="card p-5">
            <div className="mb-4 flex flex-wrap items-center gap-2"><AlertTriangle size={16} className="text-orange-400" />
              <h2 className="font-medium capitalize text-white">{human(c.new.topic)} changed</h2><Badge k={c.status} /><Badge k="gemini">{c.classification}</Badge></div>
            <div className="grid gap-3 md:grid-cols-2">
              <Side label="Old decision" x={c.old} tone="border-ink-600 bg-ink-800" />
              <Side label="New decision" x={c.new} tone="border-violet-700/70 bg-violet-950/20" />
            </div>
            <p className="mt-4 text-sm text-slate-300"><span className="text-slate-500">Why flagged: </span>{c.explanation}</p>
            {c.status === 'open' ? (
              <div className="mt-4 flex flex-wrap gap-2">
                <button className="btn-primary" onClick={() => resolve(c.id, 'supersede', 'Old decision superseded. History kept.')}>Supersede old decision</button>
                <button className="btn-ghost" onClick={() => resolve(c.id, 'keep', 'Old decision kept. New one rejected.')}>Keep old decision</button>
                <button className="btn-ghost" onClick={() => resolve(c.id, 'keep_both', 'Marked resolved. Both decisions kept.')}>Mark resolved, keep both</button>
              </div>) : <p className="mt-4 text-sm text-emerald-400">Resolved: {{ supersede: 'old decision superseded', keep: 'old decision kept', keep_both: 'both decisions kept' }[c.resolution]}.</p>}
          </section>))}</div>}
    </>
  )
}

/* ---------------- Tasks ---------------- */
function Review({ t, act, api, members = [] }) {
  const [f, setF] = useState({ title: t.title, description: t.description || '', owner: t.owner, deadline: t.deadline || '', priority: t.priority })
  const save = () => api.put(`/tasks/${t.id}`, f)
  return (
    <div className={`card p-3 ${t.owner === 'Owner unclear' ? 'border-amber-700/50' : ''}`}>
      <div className="grid gap-2 md:grid-cols-[1fr_150px_150px_110px]">
        <input className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} aria-label="Task title" />
        <input className="input" value={f.owner} readOnly aria-label="Owner" />
        <input className="input" type="date" value={f.deadline} onChange={(e) => setF({ ...f, deadline: e.target.value })} aria-label="Deadline" />
        <select className="input" value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })} aria-label="Priority"><option>low</option><option>medium</option><option>high</option></select>
      </div>
      <select className="input mt-2" aria-label="Assign to a team member" value={f.assignee_user_id === undefined ? (t.assignee_user_id || '') : (f.assignee_user_id || '')} onChange={(e) => { const id = e.target.value ? Number(e.target.value) : null; setF({ ...f, assignee_user_id: id, owner: members.find((m) => m.id === id)?.name || 'Owner unclear' }) }}><option value="">Unassigned / select a member</option>{members.filter((m) => m.department_id === t.department_id).map((m) => <option key={m.id} value={m.id}>{m.name} ({m.email})</option>)}</select>
      <textarea className="input mt-2 h-16" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} aria-label="Description" />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <div className="mr-auto flex flex-wrap items-center gap-2 text-xs text-slate-500">{t.status === 'done' && <Badge k="resolved">Reported done in a later meeting</Badge>}{t.quote && <span>{t.meeting_title}: “{t.quote}”</span>}</div>
        <button className="btn-primary" onClick={() => act(async () => { await save(); return api.post(`/tasks/${t.id}/approve`, { approved: true }) }, 'Task approved')}><Check size={14} /> Approve</button>
        <button className="btn-ghost" onClick={() => act(save, 'Changes saved')}>Save edits</button>
        <button className="btn-danger" onClick={() => act(() => api.post(`/tasks/${t.id}/approve`, { approved: false }), 'Task rejected')}><X size={14} /> Reject</button>
      </div>
    </div>
  )
}
function Tasks({ d, act, api, user }) {
  const [nt, setNt] = useState({ title: '', owner: '', deadline: '' })
  const [members, setMembers] = useState([]), [departments, setDepartments] = useState([])
  useEffect(() => { if (user.role !== 'employee') { api.get('/organization/members').then((r) => setMembers(r.data)); api.get('/organization/departments').then((r) => setDepartments(r.data)) } }, [api, user.role])
  const pending = d.tasks.filter((t) => t.approval === 'pending')
  const board = d.tasks.filter((t) => t.approval === 'approved')
  const rejected = d.tasks.filter((t) => t.approval === 'rejected')
  const cols = [['todo', 'To do'], ['in_progress', 'In progress'], ['done', 'Done']]
  const gh = d.integ?.github
  return (
    <>
      <Title sub="Review what the agent extracted. Nothing reaches GitHub until you approve it.">Tasks</Title>
      {user.role !== 'employee' && <><h2 className="mb-2 text-sm font-medium text-white">Needs your review ({pending.length})</h2>
      <div className="mb-8 space-y-3">{pending.length === 0 ? <Empty>No tasks waiting for approval.</Empty> : pending.map((t) => <Review key={t.id + t.title + t.owner + t.deadline} t={t} act={act} api={api} members={members} />)}</div></>}
      <div className="mb-2 flex flex-wrap items-center gap-2"><h2 className="mr-auto text-sm font-medium text-white">Board</h2>
        {user.role !== 'employee' && <>
        <input className="input !w-44" placeholder="Add a task" value={nt.title} onChange={(e) => setNt({ ...nt, title: e.target.value })} />
        {user.role === 'admin' && <select className="input !w-36" aria-label="Task department" value={nt.department_id || ''} onChange={(e) => setNt({ ...nt, department_id: e.target.value ? Number(e.target.value) : null, assignee_user_id: null })}><option value="">No department</option>{departments.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>}
        <select className="input !w-40" aria-label="Task assignee" value={nt.assignee_user_id || ''} onChange={(e) => setNt({ ...nt, assignee_user_id: e.target.value ? Number(e.target.value) : null })}><option value="">Unassigned</option>{members.filter((x) => x.department_id === (user.role === 'admin' ? (nt.department_id || null) : user.department_id)).map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
        <input className="input !w-36" type="date" value={nt.deadline} onChange={(e) => setNt({ ...nt, deadline: e.target.value })} />
        <button className="btn-ghost" disabled={!nt.title.trim()} onClick={async () => { const r = await act(() => api.post('/tasks', nt), 'Task added'); if (r) setNt({ title: '', owner: '', deadline: '' }) }}><Plus size={14} /> Add</button></>}</div>
      <div className="grid gap-4 md:grid-cols-3">{cols.map(([k, label]) => (
        <section key={k} className="rounded-xl bg-ink-900/60 p-3"><h3 className="mb-3 flex justify-between text-sm text-slate-400">{label}<span>{board.filter((t) => t.status === k).length}</span></h3>
          <div className="space-y-2">{board.filter((t) => t.status === k).map((t) => (
            <div key={t.id} className="card p-3 text-sm">
              <div className="text-white">{t.title}</div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs"><Badge k={t.priority} /><span className={t.owner === 'Owner unclear' ? 'text-amber-300' : 'text-slate-400'}>{t.owner}</span><span className="text-slate-500">{fmt(t.deadline)}</span></div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <select className="input !w-auto !py-1 text-xs" value={t.status} aria-label="Status" onChange={(e) => act(() => api.put(`/tasks/${t.id}`, { status: e.target.value }))}>{cols.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                {user.role !== 'employee' && (t.sync_status === 'synced' ? <a className="flex items-center gap-1 text-xs text-blue-400 hover:underline" href={t.issue_url} target="_blank" rel="noreferrer"><GitBranch size={12} /> #{t.issue_number} <ExternalLink size={11} /></a>
                  : <button className="btn-ghost !px-2 !py-1 text-xs" disabled={t.sync_status === 'syncing' || t.sync_status === 'uncertain'} title={gh?.configured ? 'Create GitHub issue' : 'GitHub is not configured'} onClick={() => act(() => api.post(`/tasks/${t.id}/sync`), 'GitHub issue created')}><GitBranch size={12} /> {t.sync_status === 'syncing' ? 'Creating issue…' : 'Create issue'}</button>)}
              </div>
              {['failed', 'uncertain'].includes(t.sync_status) && <p className="mt-2 text-xs text-red-400">{t.sync_error}</p>}
              {user.role !== 'employee' && <details className="mt-2"><summary className="cursor-pointer text-xs text-slate-400">Edit or review task</summary><Review t={t} act={act} api={api} members={members} /></details>}
            </div>))}</div></section>))}</div>
      {rejected.length > 0 && <details className="mt-6"><summary className="cursor-pointer text-sm text-slate-400">Rejected tasks ({rejected.length})</summary><div className="mt-2 space-y-2">{rejected.map((t) => <Review key={t.id} t={t} act={act} api={api} members={members} />)}</div></details>}
    </>
  )
}

/* ---------------- Reminders ---------------- */
function Reminders({ api, advance, notes, version, user }) {
  const [r, setR] = useState(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => { setError(''); api.get('/reminders').then((x) => setR(x.data)).catch((e) => { setR(null); setError(errMsg(e)) }) }, [api, version, retry])
  if (error) return <div className="card space-y-3 p-5"><p role="alert" className="text-sm text-red-300">Could not load reminders: {error}</p><button className="btn-ghost" onClick={() => setRetry((n) => n + 1)}>Try again</button></div>
  if (!r) return <Loader2 className="animate-spin text-slate-500" />
  const groups = [['overdue', 'Overdue', 'text-red-400'], ['due_today', 'Due today', 'text-orange-400'], ['due_soon', 'Due within 2 days', 'text-amber-300'],
    ['upcoming', 'Upcoming', 'text-slate-200'], ['completed', 'Completed', 'text-emerald-400'], ['no_deadline', 'No deadline set', 'text-slate-400']]
  return (
    <>
      <Title sub="Deadlines are stored as real dates. Demo mode moves only the app’s clock.">Reminders</Title>
      <div className="card mb-5 flex flex-wrap items-center gap-3 p-4">
        <div className="mr-auto text-sm"><div className="text-slate-400">Real date: <span className="text-slate-200">{fmt(r.clock.real_date)}</span></div>
          <div className={r.clock.simulated ? 'text-amber-300' : 'text-slate-400'}>App date: {fmt(r.clock.sim_date)}{r.clock.simulated && ` (simulated, +${r.clock.offset_days} days)`}</div></div>
        {user.role === 'admin' && <><button className="btn-primary" onClick={() => advance({ days: 2 })}><FastForward size={14} /> Advance Time by 2 Days</button>
        <button className="btn-ghost" onClick={() => advance({ to_next_deadline: true })}>Jump to 2 days before next deadline</button>
        <button className="btn-ghost" onClick={() => advance({ reset: true })}><RotateCcw size={14} /> Use real date</button></>}
      </div>
      {notes.length > 0 && <div className="mb-5 rounded-xl border border-amber-700/60 bg-amber-950/30 p-4 text-sm"><h2 className="mb-2 font-medium text-amber-200">Needs attention after the last time change</h2>
        {notes.map((n) => <p key={n.task_id} className="text-amber-100">{n.owner} has “{n.title}” {n.state === 'overdue' ? 'overdue since' : n.state === 'due_today' ? 'due today,' : 'due'} {fmt(n.deadline)}.</p>)}</div>}
      <div className="grid gap-4 md:grid-cols-2">{groups.map(([k, label, c]) => (
        <section key={k} className="card p-4"><h2 className={`mb-2 text-sm font-medium ${c}`}>{label} ({r[k].length})</h2>
          {r[k].length === 0 ? <p className="text-sm text-slate-600">Nothing here.</p> : <ul className="space-y-1.5">{r[k].map((t) => <li key={t.id} className="flex justify-between gap-3 text-sm"><span className="min-w-0 break-words text-slate-200">{t.title} <span className="text-slate-500">· {t.owner}</span></span><span className="shrink-0 text-slate-500">{fmt(t.deadline)}</span></li>)}</ul>}</section>))}</div>
    </>
  )
}

/* ---------------- Digest ---------------- */
function Digest({ api, toast, version, user }) {
  const [people, setPeople] = useState([])
  const [who, setWho] = useState('')
  const [dg, setDg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [team, setTeam] = useState(null)
  const [peopleError, setPeopleError] = useState('')
  const [peopleRetry, setPeopleRetry] = useState(0)
  useEffect(() => { setPeopleError(''); api.get('/people').then((r) => { setPeople(r.data); setWho((w) => w || r.data[0] || '') }).catch((e) => setPeopleError(errMsg(e))) }, [api, version, peopleRetry])
  const gen = async () => {
    setBusy('individual')
    try { setDg((await api.get(`/digest/${encodeURIComponent(who)}`)).data) } catch (e) { toast(errMsg(e), 'err') }
    setBusy(false)
  }
  const List = ({ title, items }) => (<div><h3 className="mb-1 text-sm font-medium text-white">{title} ({items.length})</h3>
    {items.length === 0 ? <p className="text-sm text-slate-600">None</p> : items.map((t, i) => <p key={i} className="text-sm text-slate-400">{t.title} {t.deadline && <span className="text-slate-600">· {fmt(t.deadline)}</span>}</p>)}</div>)
  return (
    <>
      <Title sub="A personal summary written from stored records only.">Weekly Digest</Title>
      {user.role !== 'employee' && <div className="card mb-5 p-4"><button className="btn-ghost" disabled={!!busy} onClick={async () => { setBusy('team'); try { setTeam((await api.get('/team/digest')).data) } catch (e) { toast(errMsg(e), 'err') } setBusy(false) }}>{busy === 'team' ? <Loader2 size={14} className="animate-spin" /> : <Newspaper size={14} />} {busy === 'team' ? 'Generating…' : 'Generate team weekly digest'}</button>{team && <><div className="mt-3"><Badge k={team.source}>{team.source === 'gemini' ? 'Written by Gemini' : 'Template summary (no Gemini key)'}</Badge></div><p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">{team.summary}</p></>}</div>}
      {peopleError ? <div className="card space-y-3 p-5"><p role="alert" className="text-sm text-red-300">Could not load team members: {peopleError}</p><button className="btn-ghost" onClick={() => setPeopleRetry((n) => n + 1)}>Try again</button></div> : people.length === 0 ? <Empty>No team members yet. Process a meeting first.</Empty> : (
        <>
          <div className="mb-5 flex flex-wrap gap-2"><select className="input !w-full sm:!w-48" value={who} onChange={(e) => { setWho(e.target.value); setDg(null) }} aria-label="Team member">{people.map((p) => <option key={p}>{p}</option>)}</select>
            <button className="btn-primary" disabled={!!busy} onClick={gen}>{busy === 'individual' ? <Loader2 size={14} className="animate-spin" /> : <Newspaper size={14} />} {busy === 'individual' ? 'Generating…' : 'Generate digest'}</button></div>
          {dg && <div className="space-y-4"><div className="card p-5"><div className="mb-2 flex items-center gap-2"><h2 className="font-medium text-white">{dg.data.person}, as of {fmt(dg.data.as_of)}</h2>
            <Badge k={dg.source}>{dg.source === 'gemini' ? 'Written by Gemini' : 'Template summary (no Gemini key)'}</Badge></div><p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{dg.summary}</p></div>
            <div className="card grid gap-5 p-5 sm:grid-cols-2 lg:grid-cols-4"><List title="Completed" items={dg.data.completed} /><List title="Pending" items={dg.data.pending} /><List title="Overdue" items={dg.data.overdue} /><List title="Upcoming" items={dg.data.upcoming} /></div>
            {dg.data.unresolved_conflicts.length > 0 && <div className="card border-orange-800/60 p-4 text-sm text-orange-200">Unresolved conflicts: {dg.data.unresolved_conflicts.map((c) => `${human(c.topic)} (${c.old} vs ${c.new})`).join('; ')}</div>}</div>}
        </>)}
    </>
  )
}

/* ---------------- Integrations ---------------- */
function Integrations({ d, act, api }) {
  const g = d.integ?.github
  const [f, setF] = useState({ token: '', owner: '', repo: '' })
  useEffect(() => { if (g) setF((x) => ({ ...x, owner: g.owner, repo: g.repo })) }, [g?.owner, g?.repo])
  return (
    <>
      <Title sub="Both integrations are optional. The Kanban board works without them.">Integrations</Title>
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card p-5"><div className="mb-2 flex items-center gap-2"><Sparkles size={16} className="text-violet-400" /><h2 className="font-medium text-white">Gemini</h2>
          <Badge k={d.integ?.gemini.configured ? 'resolved' : 'pending'}>{d.integ?.gemini.configured ? 'Configured' : 'Not configured'}</Badge></div>
          <p className="text-sm text-slate-400">Used for extraction, conflict comparison and digests. Set <code>GEMINI_API_KEY</code> in <code>backend/.env</code> and restart the backend. Model: {d.integ?.gemini.model}.</p></section>
        <section className="card space-y-2.5 p-5"><div className="mb-1 flex items-center gap-2"><GitBranch size={16} /><h2 className="font-medium text-white">GitHub Issues</h2>
          <Badge k={g?.configured ? 'resolved' : 'pending'}>{g?.configured ? 'Configured' : 'Not configured'}</Badge></div>
          <input className="input" type="password" placeholder={g?.token_set ? 'Token saved (enter a new one to replace)' : 'Personal access token'} value={f.token} onChange={(e) => setF({ ...f, token: e.target.value })} />
          <div className="grid grid-cols-2 gap-2"><input className="input" placeholder="Owner" value={f.owner} onChange={(e) => setF({ ...f, owner: e.target.value })} /><input className="input" placeholder="Repository" value={f.repo} onChange={(e) => setF({ ...f, repo: e.target.value })} /></div>
          <div className="flex gap-2"><button className="btn-primary" onClick={async () => { await act(() => api.put('/integrations/github', f), 'GitHub settings saved'); setF({ ...f, token: '' }) }}>Save</button>
            <button className="btn-ghost" onClick={() => act(() => api.post('/integrations/github/test'), (r) => `Connected to ${r.full_name}`)}>Test connection</button></div>
          <p className="text-xs text-slate-500">The token needs permission to create issues in the repository. Issues are created only for approved tasks.</p></section>
      </div>
    </>
  )
}

function Organization({ api, user, toast, d, section }) {
  const [members, setMembers] = useState([]), [departments, setDepartments] = useState([]), [name, setName] = useState(''), [busy, setBusy] = useState(false)
  const [inviteEmail, setInviteEmail] = useState(''), [inviteRole, setInviteRole] = useState('employee'), [invitation, setInvitation] = useState(null)
  const load = async () => { try { const [m, dep] = await Promise.all([api.get('/organization/members'), api.get('/organization/departments')]); setMembers(m.data); setDepartments(dep.data) } catch (e) { toast(errMsg(e), 'err') } }
  useEffect(() => { load() }, [])
  const save = async (id, values) => { try { await api.put(`/organization/members/${id}`, values); toast('Member updated'); await load() } catch (e) { toast(errMsg(e), 'err') } }
  const shown = members.filter((m) => section === 'employees' ? m.role === 'employee' : section === 'managers' ? (m.role === 'manager' || m.manager_requested) : true)
  return <><Title sub="Roles and department membership are enforced by the server.">{section ? section[0].toUpperCase() + section.slice(1) : user.role === 'admin' ? 'Organization' : 'Team Members'}</Title>
    <div className="mb-4 grid gap-3 sm:grid-cols-3"><div className="card p-4"><div className="text-2xl text-white">{members.filter((m) => m.role === 'employee').length}</div><div className="text-sm text-slate-400">Employees</div></div><div className="card p-4"><div className="text-2xl text-white">{members.filter((m) => m.role === 'manager').length}</div><div className="text-sm text-slate-400">Managers</div></div><div className="card p-4"><div className="text-2xl text-white">{departments.length}</div><div className="text-sm text-slate-400">Departments</div></div></div>
    {user.role === 'admin' && !user.is_demo && ['employees','managers'].includes(section) && <div className="card mb-4 space-y-3 p-4"><h2 className="font-medium text-white">Invite a member</h2><p className="text-xs text-slate-400">Create a single-use code for a specific email. Share it securely; the code expires in seven days. Manager requests still need approval.</p><div className="flex flex-wrap gap-2"><input className="input !w-full sm:!w-64" type="email" placeholder="Member email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} /><select className="input !w-36" aria-label="Invitation role" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}><option value="employee">Employee</option><option value="manager">Manager</option></select><button className="btn-primary" disabled={busy || !inviteEmail.trim()} onClick={async () => { setBusy(true); setInvitation(null); try { setInvitation((await api.post('/organization/invitations',{ email:inviteEmail, role:inviteRole })).data); toast('Invitation created') } catch (e) { toast(errMsg(e),'err') } setBusy(false) }}>Create invitation</button></div>{invitation && <div><p className="mb-1 text-xs text-amber-200">Copy this code now; it will not be shown again.</p><input className="input" aria-label="Invitation code" readOnly value={invitation.invitation_code} /></div>}</div>}
    {user.role === 'admin' && section === 'departments' && <div className="card mb-4 flex gap-2 p-4"><input className="input" placeholder="New department name" value={name} onChange={(e) => setName(e.target.value)} /><button className="btn-primary" disabled={busy || !name.trim()} onClick={async () => { setBusy(true); try { await api.post('/organization/departments', { name }); setName(''); await load(); toast('Department created') } catch (e) { toast(errMsg(e), 'err') } setBusy(false) }}>Create department</button></div>}
    {!['departments','reports'].includes(section) && <div className="card divide-y divide-ink-700">{shown.length === 0 ? <p className="p-4 text-sm text-slate-400">No members in this view yet.</p> : shown.map((m) => <MemberRow key={`${m.id}-${m.role}-${m.department_id}`} member={m} departments={departments} editable={user.role === 'admin' && !user.is_demo} save={save} tasks={d.tasks} />)}</div>}
    {user.role === 'admin' && departments.length > 0 && ['departments','reports'].includes(section) && <section className="card mt-4 p-4"><h2 className="mb-3 font-medium text-white">Department progress</h2>{departments.map((dep) => { const ts = d.tasks.filter((t) => t.department_id === dep.id && t.approval !== 'rejected'); return <div className="flex justify-between py-1 text-sm text-slate-300" key={dep.id}><span>{dep.name}</span><span>{ts.filter((t) => t.status === 'done').length} / {ts.length} tasks complete</span></div> })}</section>}
    {user.role === 'admin' && <p className="mt-4 text-sm text-slate-400">{user.is_demo ? 'Demo identities are fixed. Sign out and start a new demo to preview another role.' : 'Members join using an invitation. A manager request starts as an employee until an admin changes the role.'}</p>}
  </>
}

function MemberRow({ member, departments, editable, save, tasks }) {
  const [role, setRole] = useState(member.role), [dep, setDep] = useState(member.department_id || '')
  const assigned = tasks.filter((t) => t.assignee_user_id === member.id && t.approval !== 'rejected')
  return <div className="flex flex-wrap items-center gap-3 p-4"><div className="mr-auto"><div className="text-sm font-medium text-white">{member.name} {member.manager_requested ? <Badge k="pending">Manager requested</Badge> : null}</div><div className="text-xs text-slate-400">{member.email} · {assigned.filter((t) => t.status === 'done').length} / {assigned.length} tasks complete</div></div>
    {editable ? <><select className="input !w-auto" aria-label={`Role for ${member.name}`} value={role} onChange={(e) => setRole(e.target.value)}><option value="employee">Employee</option><option value="manager">Manager</option><option value="admin">Admin</option></select><select className="input !w-auto" aria-label={`Department for ${member.name}`} value={dep} onChange={(e) => setDep(e.target.value)}><option value="">No department</option>{departments.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select><button className="btn-ghost" onClick={() => save(member.id, { role, department_id: dep ? Number(dep) : null })}>Save</button>{member.manager_requested && <button className="btn-ghost" onClick={() => save(member.id, { decline_manager_request: true })}>Decline request</button>}</> : <span className="text-sm text-slate-400">{member.role}</span>}</div>
}

/* ---------------- Settings ---------------- */
function Settings({ act, api, advance, user }) {
  if (user.is_demo) return <><Title sub="This sandbox belongs only to your demo session.">Demo settings</Title><div className="card space-y-3 p-5"><h2 className="font-medium text-white">Reset demo sandbox</h2><p className="text-sm text-slate-400">Restore the example meetings, tasks, and decisions in your sandbox.</p><button className="btn-ghost" onClick={() => window.confirm('Reset your demo sandbox to its starting data?') && act(() => api.post('/demo/sandbox/reset'), 'Your demo sandbox was reset')}>Reset demo</button></div></>
  return (
    <>
      <Title sub="Demo controls for running the full workflow.">Settings</Title>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="card space-y-3 p-5"><h2 className="font-medium text-white">Demo data</h2>
          <p className="text-sm text-slate-400">Loading is safe to repeat. Existing demo meetings are never duplicated.</p>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" onClick={() => act(() => api.post('/demo/load'), (r) => `${r.created} meetings added, ${r.processed} processed`)}>Load and process all three</button>
            <button className="btn-ghost" onClick={() => act(() => api.post('/demo/load?process=0'), (r) => `${r.created} transcripts added. Process them one by one.`)}>Load transcripts only</button></div></section>
        <section className="card space-y-3 p-5"><h2 className="font-medium text-white">Reset</h2>
          <p className="text-sm text-slate-400">Removes all meetings, decisions, tasks and activity from the database.</p>
          <div className="flex gap-2"><button className="btn-danger" onClick={() => window.confirm('Delete all MeetFlow data?') && act(() => api.post('/demo/reset'), 'All data cleared')}>Clear all data</button>
            <button className="btn-ghost" onClick={() => advance({ reset: true })}>Use real date</button></div></section>
      </div>
    </>
  )
}
