# Team Pulse — CLAUDE.md

Zero-input async standup tool. Generates daily standup digests from signals the team already produces (GitHub activity, etc.) — no forms, no Slack-bot nags.

**Status (2026-06-24):** GitHub webhook integration complete and verified with real events. AI synthesis engine live — `POST /digest/generate` calls Claude Haiku and returns plain-English standup summaries. Next: additional integrations, Slack delivery, scheduler, auth.

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
- `anthropic>=0.40.0`

**Config** — copy `backend/.env.example` → `backend/.env` and fill in:
```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-service-role-or-anon-key
APP_ENV=development
GITHUB_WEBHOOK_SECRET=   # needed for webhook HMAC verification
ANTHROPIC_API_KEY=       # for /digest/generate
```

**Structure:**
```
backend/app/
├── main.py                         # FastAPI app, CORS, router registration
├── config.py                       # Pydantic settings (reads .env via lru_cache)
├── routes/
│   ├── health.py                   # GET /health
│   ├── digest.py                   # POST /digest/generate
│   └── webhooks/
│       └── github.py               # POST /webhooks/github
├── integrations/
│   └── supabase_client.py          # get_supabase() — cached Supabase client
├── services/                       # business logic (empty)
└── models/
    ├── activity_event.py           # ActivityEvent Pydantic model
    └── standup.py                  # StandupEntry model
```

**Routes:**
- `GET /` → `{"name": "Team Pulse API", "version": "0.1.0"}`
- `GET /health` → service status + supabase_configured flag
- `POST /webhooks/github` → receives GitHub webhook events, normalizes, stores to Supabase
- `POST /digest/generate?actor=<github-login>` → queries last 24h of events for actor, calls Claude Haiku, returns summary JSON

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

Project ref: `kszyczizrhfpuwgvcgva`

`activity_events` table is live. Schema:

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

The timestamp column is `received_at` (not `created_at`).

---

## GitHub Webhook Integration (complete)

**What's built:**
- `POST /webhooks/github` in `backend/app/routes/webhooks/github.py`
- HMAC-SHA256 signature verification via `X-Hub-Signature-256` (skipped when `GITHUB_WEBHOOK_SECRET` is empty)
- Handles `pull_request` events (opened, closed, merged) and `push` events (one row per commit)
- Normalizes to `ActivityEvent` and batch-inserts to Supabase

**Event normalization rules:**
- `pull_request` / opened → `pr_opened`
- `pull_request` / closed + merged=true → `pr_merged`
- `pull_request` / closed + merged=false → `pr_closed`
- `push` → one `commit_pushed` event per commit in `payload.commits`

**Verified:** Real PR events from GitHub (num-err PR #1 on `num-err/team-pulse`) produced 5 rows in `activity_events`.

---

## ngrok / Local Tunnel

ngrok is installed and the authtoken is configured. To expose the backend:

```bash
ngrok http 8000
```

The public URL goes in the GitHub webhook settings as:
`https://<subdomain>.ngrok-free.app/webhooks/github`

Webhook registered on: `github.com/num-err/team-pulse` → Settings → Webhooks
- Content type: `application/json`
- Events: pull requests, pushes (or "Send me everything")

---

## AI Synthesis Engine (complete)

**Endpoint:** `POST /digest/generate?actor=<github-login>`

**What it does:**
1. Queries Supabase for all `activity_events` where `actor = ?` and `received_at >= now() - 24h`
2. Formats events as a text list and sends to Claude Haiku (`claude-haiku-4-5`) via Anthropic SDK
3. Returns a 2–4 sentence plain-English summary in third person

**System prompt:**
> "You are a progress summarization assistant for a software team. Given the following raw activity data for {actor} on {date}, write a 2-4 sentence plain-English summary of what they accomplished. Write in third person. Be specific. Keep it under 100 words. No bullet points."

**Response shape:**
```json
{
  "summary": "On 2026-06-24, num-err ...",
  "actor": "num-err",
  "date": "2026-06-24",
  "event_count": 6
}
```

**Implementation notes:**
- `anthropic.Anthropic(api_key=get_settings().anthropic_api_key)` — key passed explicitly because uvicorn doesn't auto-load `.env` into `os.environ`
- Model: `claude-haiku-4-5`, `max_tokens=256`
- Returns 404 if no events found for actor in the last 24 hours

---

## What's Next (not yet built)

| Area | Detail |
|---|---|
| Additional integrations | Notion, Figma, Linear — each needs its own webhook/polling route and normalizer |
| Slack delivery | Send the digest summary to a Slack channel or DM via Slack API |
| Scheduler | Daily cron (e.g. APScheduler or a Supabase Edge Function) to call `/digest/generate` for each team member automatically |
| Auth | Who can request whose digest? GitHub OAuth or API key middleware |
| Dashboard with real data | Wire `app/dashboard/page.tsx` to call `POST /digest/generate` and display live summaries instead of mock data |
| Multi-actor digest | Team-level rollup across all actors for a given day |

---

## Git

- Remote: `https://github.com/num-err/team-pulse`
- Branch: `main`
