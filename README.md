# MeetFlow AI

**From conversations to commitments. Automatically.**

An agentic meeting assistant for the Product Space Agentic AI Hackathon (PS 03: Meeting-to-Execution Agent).
It turns transcripts into decisions and tasks, remembers them across meetings, flags contradictions for human review,
and only sends work to GitHub after approval.

## What makes it agentic
Each meeting runs through **Observe → Reason → Plan → Request approval → Execute → Remember**, shown live on the meeting page.
- **Observe/Reason:** Gemini extracts summary, decisions, tasks, owners, deadlines and quotes (JSON response schema, validated server-side).
- **Memory:** decisions, tasks, conflicts and history persist in SQLite.
- **Conflict detection:** new decisions are sent to Gemini with all active historical decisions. Gemini classifies each pair as
  `contradicts`, `updates`, `duplicate` or `unrelated`, with an explanation. Invalid IDs or classes are discarded.
  Flagged decisions stay `pending`; the old decision is never overwritten until you click **Supersede old decision**. Superseded decisions remain in history.
- **Approval gate:** the API returns `403` if a task is synced before approval. Failed GitHub calls are recorded as failures, never as success.

## Features
Overview · Meetings · Decision Memory · Conflict review (side by side) · Tasks (review, edit, approve/reject, Kanban) ·
Reminders with simulated clock · Weekly digest per person · GitHub integration · Demo controls.
Owners are never guessed (`Owner unclear`), deadlines are never invented, and completion is recorded only when a speaker says so.

## Stack
React + Vite + Tailwind + Lucide + Axios | Flask + SQLite | Gemini API (REST) | GitHub Issues API

## Setup
Requires Python 3.10+ and Node 18+.

```bash
# Backend (terminal 1)
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then add your keys
python app.py                     # http://localhost:5001

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                       # http://localhost:5173 (proxies /api to :5001)
```

### Environment (`backend/.env`)
| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Required for live AI on your own transcripts |
| `GEMINI_MODEL` | Optional, default `gemini-3.1-flash-lite` |
| `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO` | Optional. Can also be entered under **Integrations** |
| `GITHUB_ENV_ORGANIZATION_ID` | Optional organization ID permitted to use the process-wide GitHub environment values. If unset, they apply only to the legacy `MeetFlow Demo` workspace; other organizations configure their own integration in the UI. Anonymous demo sandboxes cannot use GitHub. |
| `DATABASE_PATH` | Optional absolute SQLite file path. Its parent directory must exist and be writable. Mount a persistent volume for hosted deployments. |
| `PORT` | HTTP port (default `5001`). |
| `ALLOWED_ORIGINS` | Optional comma-separated extra browser origins allowed to make changes. Default `http://localhost:5173`; same-origin requests are allowed. |
| `SESSION_SECRET` | A long random secret for signing session cookies. If unset, a local secret file is generated in the organization data directory. Keep it secret and stable across restarts. |
| `COOKIE_SECURE` | Set to `true` behind HTTPS so browsers send session cookies only over HTTPS. |
| `ORGANIZATION_DATA_DIR`, `AUTH_DATABASE_PATH` | Optional paths for the organization SQLite files and account registry. Defaults are under `meetflow-organizations` beside `DATABASE_PATH`. Persist and back up both. |

Without `GEMINI_API_KEY`, the three demo transcripts run on a deterministic fallback, clearly labelled **Demo fallback data**.
Your own transcripts return a clear "key not set" error instead of fake results.

## Use your own meetings
Open **Meetings**, enter a title, date and speaker-labelled transcript, and select **Save meeting** then **Process with agent**. Add another meeting and process it to compare its decisions against active decision memory. Review proposed changes under **Conflicts** and tasks under **Tasks**. You do not need to load the demos. Duplicate meeting submissions are rejected; each meeting is processed at most once. Quotes that cannot be found in the transcript are omitted and reported in follow-ups. AI extraction and comparison are probabilistic: review results before acting on them.

## Accounts and workspaces
On the sign-in screen select **Create an account** and create an organization with a unique name, email and password; its creator becomes its administrator. To add a member, an administrator creates an invitation under **Employees** or **Managers** and securely shares the single-use code with that person. Invitations are bound to the specified email and expire after seven days. A manager request starts as an employee until an administrator grants the manager role. Existing administrators can also grant administrator access. Never share the local session secret or database files.

Administrators create departments and assign members to them. Managers can view and manage their assigned department; employees see approved tasks assigned to their user ID and meetings they participate in. A manager or admin adds meeting participants on the meeting page. For a reliable assignment, select a registered user in task review; automatic owner matching requires a unique exact name in the department. A participant or an assignee is notified when a related decision is flagged. Changes to a user's role take effect on the next API request; sign out and back in to refresh the navigation.

The first startup copies the previous local database into an isolated **MeetFlow Demo** organization and leaves the original in place. To claim that legacy workspace, select **Claim the existing demo workspace**, use organization name `MeetFlow Demo`, and enter the one-time claim code stored locally in `backend/meetflow-organizations/demo-claim-code.txt` (or in `ORGANIZATION_DATA_DIR` if configured). Only the first administrator can claim it; subsequent members use invitations. The copy includes all records from the original database, including any non-demo meetings and saved integration settings; share it only with trusted members.

## Explore Demo Workspace
The sign-in page offers a demo that asks for a display name and role but no account. Each session gets a separate SQLite sandbox with fictional people, meetings, tasks, and an open conflict. The supplied name appears in the greeting; the selected fictional person's data remains labelled as such. Choose a role before starting; sign out and start a new demo to try another role. Use **Reset demo** to restore the current session's sample data. The seeded results are labelled as demo fallback; user-entered transcripts require the configured Gemini key and are labelled Gemini. No real accounts, saved integration credentials, or legacy demo records are copied into these sandboxes. GitHub actions are disabled. Sandboxes expire after 12 hours and are deleted on logout or cleaned up when a later demo session starts. A demo session allows up to 12 AI-enabled actions (some make multiple Gemini calls) and 250 changes; demo starts are limited per source address. Resetting does not reset these limits. Configure the proxy to pass a trustworthy client address and apply external rate limits before public deployment.

Transcripts are sent to Gemini for processing. The application treats transcript text as untrusted data in the model prompt, but prompt-injection resistance and AI output are not guaranteed. GitHub issue creation requires a separately approved task and an explicit Create issue action.

## Production deployment
The repository includes a multi-stage `Dockerfile` that builds the frontend and serves it with Flask using Waitress. Set `GEMINI_API_KEY` and `SESSION_SECRET` as secrets in the hosting environment; never place them in frontend build variables. Set `COOKIE_SECURE=true` behind HTTPS. Mount a durable volume at `/data` and use the default `DATABASE_PATH=/data/meetflow.db`; the account registry and per-organization databases are stored under `/data/meetflow-organizations`. Use one application instance with persistent storage; do not use ephemeral container storage or share the files across machines. Back up the entire directory and legacy database together using a consistent storage snapshot. For example:

```bash
docker build -t meetflow .
docker run --rm -p 5001:5001 --env-file ./backend/.env -e DATABASE_PATH=/data/meetflow.db -v meetflow-data:/data meetflow
```

The resulting application is at `http://localhost:5001`. Set the platform's `PORT` if required and terminate HTTPS at the hosting platform. Use a host supporting persistent volumes; local Docker volumes are not a hosted public URL.

**Access limitation:** passwords are hashed and server-side sessions are revocable; organizations use separate SQLite files. Invitations verify possession of a single-use code bound to an email address, but there is no email delivery or independent verification of mailbox ownership. Session and access controls have not had an independent security audit. GitHub tokens entered in the UI are stored in plaintext in the organization database. Restrict access to the volume; do not store sensitive production data without further security review, email verification, credential protection, and operational abuse controls. No public deployment is configured by this repository.

## Demo script
1. **Settings → Load transcripts only**, then open **Meetings** and click *Process with agent* on Monday, then Wednesday
   (or use **Load and process all three**).
2. **Conflicts:** December 10 vs December 15 appears side by side. Click **Supersede old decision**; check **Decision Memory** for the history.
3. **Tasks:** review Friday's tasks. "Prepare deployment checklist" stays `Owner unclear`. Approve a task.
4. **Reminders:** click **Advance Time by 2 Days** (or *Jump to 2 days before next deadline*) to trigger due-soon notices.
5. **Weekly Digest:** pick Sarah and generate.
6. **Integrations:** add a GitHub token with issue access, then **Create issue** on an approved task.

## GitHub token
Create a token at GitHub → Settings → Developer settings → Personal access tokens. A fine-grained token needs
**Issues: Read and write** on the target repository. The token you enter in the UI is stored in the local SQLite file in plain text, so use a throwaway repo for demos.

## Tests
`python -m unittest -v test_auth_roles` tests registration, invitations, approval, organization isolation, task access, restart persistence and demo claiming. `python -m unittest -v test_demo_sandbox` checks role switching, isolated sandboxes, reset and original data preservation with mocked Gemini. `backend/test_flow.py` exercises the legacy demo workflow with a temporary database. `python test_user_flow.py` runs assertions against new exhibition transcripts with mocked Gemini responses. `python test_live_demo.py` and `python test_live_gemini.py` send fictional transcripts to the configured Gemini account and may incur API usage; both use temporary databases.

`python -m unittest -v test_feature_checks` verifies explicit AI errors, reminder transitions, dashboard status changes, and mocked GitHub errors. `python test_live_verification.py` sends two fictional workshop transcripts to Gemini and checks extraction, a cross-meeting conflict, and personal and team digests. It uses a temporary database and may incur API usage. To create one real, clearly labelled issue for verification, configure GitHub for a real organization and run `python test_live_github.py --organization-id ID --create-issue`; this leaves the issue in the configured repository for inspection and never prints the token.

## Not included
Background scheduler (reminders are computed on demand), real speaker diarization (speaker labels come from the transcript), email verification, invitation delivery, cross-department dependency tracking, and a separate multi-tenant database service.
