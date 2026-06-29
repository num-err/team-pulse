# Team Pulse — CLAUDE.md

Zero-input async standup tool. Generates daily standup digests from signals the team already produces (GitHub activity, etc.) — no forms, no Slack-bot nags.

**Status (2026-06-29):** GitHub webhook → AI synthesis → Slack delivery → daily scheduler → Linear webhook → Notion polling all complete and verified end-to-end. Live dashboard wired to real data. Next: auth, multi-actor digest, production deployment.

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
.venv/bin/uvicorn app.main:app --reload --port 8000
```

> Note: the venv was recreated at `/Users/numerahmed/Developer/team-pulse/backend/.venv` with Python 3.13 from Homebrew (`/opt/homebrew/bin/python3.13`). Use `.venv/bin/uvicorn` directly — `source .venv/bin/activate` may fail if the shell doesn't pick up the venv path correctly.

- Health check: http://localhost:8000/health
- Interactive docs: http://localhost:8000/docs

**Key deps** (`requirements.txt`):
- `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`
- `supabase==2.11.0`
- `pydantic==2.10.4`, `pydantic-settings==2.7.1`
- `python-dotenv==1.0.1`
- `anthropic>=0.40.0`
- `slack_sdk>=3.27.0`
- `apscheduler>=3.10.0`

**Config** — copy `backend/.env.example` → `backend/.env` and fill in:
```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-service-role-or-anon-key
APP_ENV=development
GITHUB_WEBHOOK_SECRET=        # needed for webhook HMAC verification
LINEAR_WEBHOOK_SECRET=        # from Linear Settings → API → Webhooks → signing secret
FIGMA_WEBHOOK_PASSCODE=       # any string you choose (set when registering Figma webhook)
NOTION_TOKEN=                 # from notion.so/my-integrations → Internal Integration Secret
ANTHROPIC_API_KEY=            # for /digest/generate
SLACK_BOT_TOKEN=xoxb-...      # Slack bot token (see Slack Setup below)
SLACK_DEFAULT_CHANNEL=        # channel ID (e.g. C0BDRS74RBL) — NOT the name
DIGEST_CRON_HOUR=9            # UTC hour to run daily digest (default 9)
DIGEST_CRON_MINUTE=0          # UTC minute (default 0)
```

**Structure:**
```
backend/app/
├── main.py                         # FastAPI app, CORS, lifespan (starts APScheduler)
├── config.py                       # Pydantic settings (reads .env via lru_cache)
├── routes/
│   ├── health.py                   # GET /health
│   ├── digest.py                   # POST /digest/generate
│   ├── slack.py                    # POST /slack/deliver
│   ├── scheduler.py                # GET /scheduler/status, POST /scheduler/run-now
│   ├── notion.py                   # GET /notion/status, POST /notion/sync
│   └── webhooks/
│       ├── github.py               # POST /webhooks/github
│       ├── linear.py               # POST /webhooks/linear
│       └── figma.py                # POST /webhooks/figma (built, needs paid Figma plan)
├── integrations/
│   └── supabase_client.py          # get_supabase() — cached Supabase client
├── services/
│   ├── digest.py                   # generate_digest(actor) — core AI synthesis logic
│   ├── slack.py                    # post_digest(digest, channel) — Slack Block Kit delivery
│   ├── scheduler.py                # run_daily_digests() — cron job, tracks last run state
│   └── notion.py                   # sync_notion() — polls Notion Search API, deduplicates via last-sync timestamp
└── models/
    ├── activity_event.py           # ActivityEvent Pydantic model
    └── standup.py                  # StandupEntry model
```

**Routes:**
- `GET /` → `{"name": "Team Pulse API", "version": "0.1.0"}`
- `GET /health` → service status + supabase_configured flag
- `POST /webhooks/github` → receives GitHub webhook events, normalizes, stores to Supabase
- `POST /webhooks/linear` → receives Linear webhook events (HMAC-SHA256 via `Linear-Signature` header)
- `POST /webhooks/figma` → receives Figma webhook events (passcode in payload body) — requires paid Figma plan to register
- `POST /digest/generate?actor=<github-login>` → queries last 24h of events, calls Claude Haiku, returns summary JSON
- `POST /slack/deliver?actor=<github-login>[&channel=<id>]` → generate + post to Slack, returns digest + `slack_ts`
- `GET /scheduler/status` → last run time + per-actor results
- `POST /scheduler/run-now` → manually trigger the daily digest job immediately
- `GET /notion/status` → last Notion sync time + events stored
- `POST /notion/sync` → manually trigger a Notion poll immediately

---

## Frontend

**Run:**
```bash
cd frontend
npm run dev    # port 3000
```

- `frontend/.env.local` already created with `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Shadcn components installed: `card`, `button` — add more with `npx shadcn@latest add <component>`

**Pages:**
- `/` → landing page (`app/page.tsx`) — headline + "Go to dashboard" button
- `/dashboard` → (`app/dashboard/page.tsx`) — live client component:
  - GitHub username input → calls `POST /digest/generate` → renders AI summary card
  - "Send to Slack" button per card → calls `POST /slack/deliver`
  - "Refresh all" when 2+ actors loaded
  - Loading / error / success states per card

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

**Event sources and types stored:**
| source | event_type values |
|---|---|
| `github` | `pr_opened`, `pr_merged`, `pr_closed`, `commit_pushed` |
| `linear` | `issue_created`, `issue_started`, `issue_completed`, `issue_cancelled`, `issue_updated`, `comment_added` |
| `figma` | `file_comment`, `version_saved` |
| `notion` | `page_created`, `page_edited` |

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

**Core logic:** `backend/app/services/digest.py` → `generate_digest(actor)`

1. Queries Supabase for all `activity_events` where `actor = ?` and `received_at >= now() - 24h`
2. Formats events as a text list and sends to Claude Haiku (`claude-haiku-4-5`) via Anthropic SDK
3. Returns a 2–4 sentence plain-English summary in third person

**System prompt:**
> "You are a progress summarization assistant for a software team. Given the following raw activity data for {actor} on {date}, write a 2-4 sentence plain-English summary of what they accomplished. Write in third person. Be specific. Keep it under 100 words. No bullet points."

**Response shape:**
```json
{
  "summary": "On 2026-06-29, num-err ...",
  "actor": "num-err",
  "date": "2026-06-29",
  "event_count": 6
}
```

**Notes:**
- `anthropic.Anthropic(api_key=get_settings().anthropic_api_key)` — key passed explicitly because uvicorn doesn't auto-load `.env` into `os.environ`
- Model: `claude-haiku-4-5`, `max_tokens=256`
- Returns 404 if no events found for actor in the last 24 hours

---

## Slack Delivery (complete)

**Core logic:** `backend/app/services/slack.py` → `post_digest(digest, channel=None)`

Posts a Block Kit message to Slack:
- Header: "Team Pulse — {date}"
- Body: actor name + AI summary
- Footer: event count

**Endpoint:** `POST /slack/deliver?actor=<github-login>[&channel=<channel-id>]`
- Generates digest then delivers it in one call
- Returns digest JSON + `slack_ts` (Slack message timestamp) + `delivered: true`
- Returns 502 on Slack API error with the Slack error code in `detail`

### Slack App Setup

App name: **Teampulse** — created at api.slack.com/apps

**Current bot token scopes (`chat:write` only):**
| Scope | Purpose |
|---|---|
| `chat:write` | Post messages to channels the bot has been invited to |

**To expand Slack capabilities in future, add these scopes:**
| Scope | Needed for |
|---|---|
| `channels:read` | List public channels (to resolve names → IDs programmatically) |
| `groups:read` | Same for private channels |
| `users:read` | Look up users by email to send DMs |
| `im:write` | Send direct messages to individual users |
| `chat:write.public` | Post to channels without being invited first |

**Important:** After adding any new scope, you must click **Reinstall to Workspace** on the OAuth & Permissions page to get a new token — the existing `xoxb-` token will not gain the new scope automatically.

**Channel ID vs name:** The Slack SDK's `chat.postMessage` requires the channel ID (e.g. `C0BDRS74RBL`), not the name. To find a channel ID: open Slack in browser → navigate to channel → copy the `C...` segment from the URL. Set `SLACK_DEFAULT_CHANNEL` to the ID, not `#teampulse`.

**Bot must be invited:** The bot must be a member of any channel it posts to. In the channel, type `/invite @Teampulse`.

---

## Scheduler (complete)

**Core logic:** `backend/app/services/scheduler.py` → `run_daily_digests()`

- Queries `activity_events` for distinct actors active in the last 24h (auto-discovery — no hardcoded list)
- For each actor: calls `generate_digest()` then `post_digest()` to Slack
- Per-actor error handling — one failure doesn't block others
- Stores last run result in memory (`_last_run`) — visible via `GET /scheduler/status`

**Wired via FastAPI lifespan** (`main.py`) — starts on server boot, shuts down cleanly on exit.

**Config:**
```
DIGEST_CRON_HOUR=9    # UTC (default: 9 AM)
DIGEST_CRON_MINUTE=0
```

**Manual trigger:** `POST /scheduler/run-now` — useful for testing without waiting for cron time.

The Notion sync job is also wired into the lifespan scheduler and runs 5 minutes before the daily digest to ensure Notion activity is included.

---

## Linear Webhook Integration (complete)

**What's built:**
- `POST /webhooks/linear` in `backend/app/routes/webhooks/linear.py`
- HMAC-SHA256 signature verification via `Linear-Signature` header (skipped when `LINEAR_WEBHOOK_SECRET` is empty)
- Handles `Issue` events (create, update) and `Comment` events (create)

**Event normalization rules:**
- `Issue` / create → `issue_created` (actor = creator)
- `Issue` / update + state.type "started" → `issue_started` (actor = assignee or creator)
- `Issue` / update + state.type "completed" → `issue_completed`
- `Issue` / update + state.type "cancelled" → `issue_cancelled`
- `Issue` / update + other → `issue_updated`
- `Comment` / create → `comment_added` (actor = commenter)

**Actor:** Linear `displayName`. **Repo:** Linear team key (e.g. `ENG`).

**To register:** Linear → Settings → API → Webhooks → New webhook → URL: `https://<ngrok>/webhooks/linear` → select Issues + Comments → copy signing secret → set `LINEAR_WEBHOOK_SECRET`.

**Verified:** Test payload produced `issue_created` row in `activity_events`.

---

## Figma Webhook Integration (built, blocked on paid plan)

**What's built:**
- `POST /webhooks/figma` in `backend/app/routes/webhooks/figma.py`
- Passcode verification (Figma embeds passcode in the JSON body rather than using an HMAC header)
- Handles `FILE_COMMENT` → `file_comment` and `FILE_VERSION_UPDATE` → `version_saved`
- Skips `FILE_UPDATE` (fires on every autosave — too noisy) and `PING`

**Blocked:** Figma webhooks require a Professional (paid) plan. The endpoint is ready — once on a paid plan, register via:
```bash
curl -X POST https://api.figma.com/v2/webhooks \
  -H "X-Figma-Token: <personal-access-token>" \
  -d '{"event_type":"FILE_COMMENT","team_id":"<team-id>","endpoint":"https://<ngrok>/webhooks/figma","passcode":"<FIGMA_WEBHOOK_PASSCODE>"}'
```

---

## Notion Integration (complete — polling)

**Why polling:** Notion webhooks are not available on the free plan. Instead the scheduler polls the Notion Search API.

**What's built:**
- `backend/app/services/notion.py` → `sync_notion()` — polls `POST /v1/search` sorted by `last_edited_time`, resolves user IDs to display names, deduplicates via in-memory last-sync timestamp
- `backend/app/routes/notion.py` → `GET /notion/status`, `POST /notion/sync`
- Runs automatically 5 minutes before the daily digest via APScheduler

**Setup:**
1. Go to notion.so/my-integrations → New integration → copy the `secret_...` token
2. Set `NOTION_TOKEN=secret_...` in `.env`
3. In each Notion page/database: click `...` → Connections → connect your integration
4. Pages edited since last sync are stored as `page_created` or `page_edited` events; actor is the Notion user display name

**Verified:** Live sync produced `page_edited` row for actor `Numer Ahmed`.

---

## What's Next (not yet built)

| Area | Detail |
|---|---|
| Auth | API key or GitHub OAuth middleware — who can request whose digest? |
| Multi-actor digest | Team-level rollup across all actors for a given day |
| Slack DMs | Send each actor their own digest as a DM (needs `users:read` + `im:write` scopes) |
| Figma (unblocked) | Upgrade to Figma Professional plan to activate the already-built `/webhooks/figma` endpoint |
| Persistent scheduler state | APScheduler + Notion sync state is in-memory — lost on restart. Use APScheduler's SQLAlchemy jobstore or a Supabase table to survive restarts |
| Production deployment | Currently dev-only (uvicorn --reload + ngrok). Needs a real host (Railway, Fly.io, etc.) with persistent process + public webhook URL |
| Actor identity mapping | GitHub login, Linear displayName, and Notion display name are all separate strings. A mapping table (or a settings page) would unify them so cross-source digests are attributed to the same person |

---

## Git

- Remote: `https://github.com/num-err/team-pulse`
- Branch: `main`
