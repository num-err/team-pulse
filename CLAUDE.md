# Team Pulse — CLAUDE.md

Zero-input async standup tool. Generates daily standup digests from signals the team already produces (GitHub activity, etc.) — no forms, no Slack-bot nags.

**Status (2026-06-24):** Early scaffold. Backend and frontend are wired up and running. GitHub webhook integration is the active build.

---

## Architecture

```
team-pulse/
├── backend/    FastAPI (Python 3.13) + Supabase
└── frontend/   Next.js 14 App Router + TypeScript + Tailwind + shadcn/ui
```

---

## Backend

**Run:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- Interactive docs: http://localhost:8000/docs
- venv lives at `backend/.venv` — already created and deps installed

**Key deps** (`requirements.txt`):
- `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`
- `supabase==2.11.0`
- `pydantic==2.10.4`, `pydantic-settings==2.7.1`
- `python-dotenv==1.0.1`

**Config** — copy `backend/.env.example` → `backend/.env` and fill in:
```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-service-role-or-anon-key
APP_ENV=development
GITHUB_WEBHOOK_SECRET=   # needed for webhook HMAC verification
```

**Structure:**
```
backend/app/
├── main.py                    # FastAPI app, CORS, router registration
├── config.py                  # Pydantic settings (reads .env via lru_cache)
├── routes/
│   ├── health.py              # GET /health
│   └── webhooks/              # (to be created) webhook receivers
├── integrations/
│   └── supabase_client.py     # get_supabase() — cached Supabase client
├── services/                  # business logic (empty)
└── models/
    └── standup.py             # StandupEntry model
```

**Existing routes:**
- `GET /` → `{"name": "Team Pulse API", "version": "0.1.0"}`
- `GET /health` → service status + supabase_configured flag

---

## Frontend

**Run:**
```bash
cd frontend
npm run dev    # port 3000
```

- Deps already installed (`node_modules` present)
- Config: copy `frontend/.env.local.example` → `frontend/.env.local`
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`

**Key deps:** Next.js 14, React 18, Tailwind 3, shadcn/ui (card, button), lucide-react
- Add shadcn components: `npx shadcn@latest add <component>`

**Pages:**
- `/` → landing page (`app/page.tsx`) — headline + "Go to dashboard" button
- `/dashboard` → (`app/dashboard/page.tsx`) — 3-column card grid (currently static mock data)

---

## Database (Supabase)

No tables created yet. The next schema to define is `activity_events`:

```sql
CREATE TABLE activity_events (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  source       TEXT        NOT NULL,   -- 'github'
  event_type   TEXT        NOT NULL,   -- 'pr_opened' | 'pr_merged' | 'pr_closed' | 'commit_pushed'
  actor        TEXT        NOT NULL,   -- GitHub login
  repo         TEXT        NOT NULL,   -- 'owner/repo'
  title        TEXT,                   -- PR title or first line of commit message
  url          TEXT,                   -- HTML URL of the PR or commit
  metadata     JSONB,                  -- raw normalized payload
  received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## GitHub Webhook Integration (active build)

**Plan:**
1. Add `GITHUB_WEBHOOK_SECRET` to `config.py`
2. Create `backend/app/models/activity_event.py` — Pydantic model matching the table above
3. Create `backend/app/routes/webhooks/github.py`:
   - `POST /webhooks/github`
   - Verify `X-Hub-Signature-256` HMAC (using `hmac` + `hashlib` stdlib, no new deps)
   - Handle `X-GitHub-Event: pull_request` (actions: opened, closed, synchronize, reopened)
   - Handle `X-GitHub-Event: push` (normalize each commit)
   - Normalize to `ActivityEvent`, insert into Supabase `activity_events`
4. Register the router in `main.py`
5. Create `activity_events` table in Supabase

**Event normalization rules:**
- `pull_request` / opened → `pr_opened`
- `pull_request` / closed + merged=true → `pr_merged`
- `pull_request` / closed + merged=false → `pr_closed`
- `push` → one `commit_pushed` event per commit in `payload.commits`

---

## Git

- Branch: `main`
- Commits: `d4af386 Initial scaffold: FastAPI backend + Next.js 14 frontend`
- No remote set yet
