# Team Pulse — CLAUDE.md

Zero-input async standup tool. Generates daily standup digests from signals the team already produces (GitHub activity, etc.) — no forms, no Slack-bot nags.

**Status (2026-07-13):** GitHub webhook → AI synthesis → Slack delivery → daily scheduler → Linear webhook → Notion polling → API key auth → multi-actor team digest all complete and verified end-to-end. Dashboard redesigned around the team digest as the primary flow, with a dark/gradient UI polished for live pitches. Added blocker detection (stale in-progress Linear issues surfaced as a prominent alert card), per-actor source icons, event-count badges, a live "last updated" timestamp, a polished empty state, and a repeatable demo-data seed script (`backend/scripts/seed_demo_events.py`). Added a **person health engine** (HEALTHY / THRASHING / SILENT_STUCK / IDLE classification per actor, surfaced as dashboard alert cards + badges, a Slack "⚠ Attention" section, and folded into the AI digest tone) plus a dedicated seed script for a screen-recorded demo (`backend/scripts/seed_demo.py`) — see Person Health Engine and Demo Data Seeding sections below. This was built purely against seeded Supabase data; no webhook/integration code was touched. Dashboard now visually verified in-browser (see Frontend Dev Gotcha note below for a `.next` cache issue hit and fixed along the way), and the live-narration pitch script for this demo is finalized in `PITCH.md`, cross-checked against the actual seeded evidence numbers. Next: production deployment.

**⚠️ Backend now runs on port 8001, not 8000** — port 8000 is occupied by an unrelated local project on this machine. The live ngrok tunnel, the registered GitHub webhook, and `frontend/.env.local`'s `NEXT_PUBLIC_API_URL` all already point at 8001. See the YC Demo Prep section below for the full pre-Sunday checklist.

---

## Ship-to-Pilot Progress (full audit run 2026-07-22, executing fixes now)

A full claims-vs-reality audit was run 2026-07-22 (code-only, no memory/docs trusted as source of truth). Working the resulting task list in order, one task at a time, each verified before moving on:

- [x] **1. Railway deploy basics** — `$PORT` via Procfile, env-driven CORS, production secret guard. See Production Deployment section below.
- [x] **2. Notion cursor persistence** — floor now derived from `MAX(received_at)` in Supabase instead of an in-memory global. See Notion Integration section below.
- [x] **3. Webhook idempotency** — natural `dedup_key` per source + DB `UNIQUE` constraint + upsert with `ignore_duplicates=True`. **⚠️ Requires running `backend/migrations/0001_activity_events_dedup_key.sql` against Supabase before this is live in prod** — see Database → Migrations.
- [x] **4. Anthropic + Slack error handling** — transient Anthropic errors retried once then 503, permanent errors 502 immediately; Slack broadened to catch connection/timeout failures as 502 too. Scheduler's existing per-actor isolation verified by actually triggering a failure, not just read. See AI Synthesis Engine, Slack Delivery, and Scheduler sections.
- [x] **5. THRASHING per-repo fix** — forward-motion suppression now scoped to `(source, repo)`, not actor-wide; corrected the SILENT_STUCK/THRASHING "mutually exclusive" language to priority-ordering; **second pass same day** after investigation found the scoped fix alone let Notion/Figma volume and normal no-merge GitHub work falsely trigger THRASHING — now restricted to GitHub/Linear and requires an independent struggle signal, not just event count (chosen: precision over recall). See Person Health Engine section.
- [x] **6. Missed-run catch-up + scheduler/Notion run persistence** — both `_last_run` (scheduler) and `_last_sync` (Notion, plus its by-value-import bug) replaced with a shared `job_runs` table; `catch_up_if_missed()` + `misfire_grace_time` cover a full restart across the scheduled window. **⚠️ Requires running `backend/migrations/0002_job_runs.sql`** — see Database → Migrations.
- [x] **7. Identity mapping** — `actor_aliases` table + `resolve_actor()` wired into all 4 ingestion paths; unmapped-actor safety property and cache verified. **Backfill deferred on purpose** (chosen: (a) one-time script, to build after tests — nothing in `activity_events` needs it yet, since the seed uses canonical names and real events are still one-handle-per-source) — see Actor Identity Mapping section.
- [x] **8. Tests** — real pytest suite in `backend/tests/` (20 tests, health classification + blocker detection only, no network/live Supabase). See Backend → Tests and What's Next → Test coverage for what's still untested.

---

## YC Investor Demo — Sunday 2026-07-12

Full audit + readiness checklist run on 2026-07-09. Full details of what was found live in each section below; short version:

- [ ] **Start the backend on port 8001** before demoing — confirmed nothing was listening there as of 07-09, which means the live GitHub webhook (ngrok tunnel has been up since 07-07) is currently silently failing.
- [ ] **Re-run the demo seed script** shortly before presenting: `cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo_events.py` — clears prior demo rows and reseeds fresh cross-tool activity (GitHub + Linear + Figma + Notion, 3 actors, one deliberate 52h-stale blocker) so the 24h digest window and the blocker card both work regardless of when Sunday's session actually starts.
- [ ] **Verify the Linear webhook** in Linear → Settings → API → Webhooks still targets the current ngrok URL (couldn't verify via API access from here).
- [ ] **Don't restart the backend** between seeding and the demo — scheduler/Notion sync state is in-memory (see Scheduler section); a restart resets it and the next Notion poll will re-insert duplicate rows.
- [ ] Known gap, not yet fixed: `post_digest`/`post_team_digest` in `services/slack.py` only catch `SlackApiError` — a real network failure (not an API error response) would surface as an unhandled 500 instead of a graceful 502. Low risk but worth a one-line fix (broaden the except) if Slack delivery is part of the live demo.
- [ ] Eyeball `/dashboard` yourself in a browser before Sunday — verified via API + typecheck, not a visual screenshot.

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
.venv/bin/uvicorn app.main:app --reload --port 8001
```

> Note: the venv was recreated at `/Users/numerahmed/Developer/team-pulse/backend/.venv` with Python 3.13 from Homebrew (`/opt/homebrew/bin/python3.13`). Use `.venv/bin/uvicorn` directly — `source .venv/bin/activate` may fail if the shell doesn't pick up the venv path correctly.

> **Port is 8001, not 8000** (as of 2026-07-09) — port 8000 is occupied by an unrelated local project on this machine. The live ngrok tunnel and `frontend/.env.local` both already point at 8001.

- Health check: http://localhost:8001/health
- Interactive docs: http://localhost:8001/docs

**Tests (added 2026-07-23):**
```bash
cd backend
.venv/bin/pytest          # pytest.ini sets pythonpath=. and testpaths=tests, so this just works
.venv/bin/pytest -v       # per-test names
```
No `.env`, no network, no live Supabase required — confirmed by running the suite in a stripped environment with `SUPABASE_URL`/`SUPABASE_KEY` unset entirely. `backend/tests/test_health.py` calls `classify_actor()` directly (pure function, explicit `now` passed in — deterministic regardless of when the suite runs); `backend/tests/test_blockers.py` monkeypatches `app.services.blockers.get_supabase` with an in-memory fake. See What's Next → Test coverage for what's still untested.

**Key deps** (`requirements.txt`):
- `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`
- `supabase==2.11.0`
- `pydantic==2.10.4`, `pydantic-settings==2.7.1`
- `python-dotenv==1.0.1`
- `anthropic>=0.40.0`
- `slack_sdk>=3.27.0`
- `apscheduler>=3.10.0`
- `httpx>=0.27.0` (used directly by `notion.py`; previously only installed transitively)
- `pytest>=8.0.0` (dev-only, but kept in the same flat `requirements.txt` — no dev/prod split in this repo)

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
├── main.py                         # FastAPI app, env-driven CORS, lifespan (starts APScheduler)
├── config.py                       # Pydantic settings (reads .env via lru_cache) + validate_production_settings()
├── routes/
│   ├── health.py                   # GET /health, GET /health/team
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
│   ├── digest.py                   # generate_digest(actor) — core AI synthesis logic, returns per-actor sources + health
│   ├── team_digest.py              # generate_team_digest() — multi-actor rollup + blockers + attention
│   ├── blockers.py                 # find_blockers() — flags stale in-progress Linear issues
│   ├── health.py                   # classify_actor() / classify_team_health() / get_actor_health() — HEALTHY/THRASHING/SILENT_STUCK/IDLE
│   ├── slack.py                    # post_digest(digest, channel) — Slack Block Kit delivery
│   ├── scheduler.py                # run_daily_digests() — cron job; catch_up_if_missed() at startup
│   ├── notion.py                   # sync_notion() — polls Notion Search API, deduplicates via MAX(received_at)
│   ├── job_runs.py                 # record_run()/get_last_run() — shared restart-safe job-status persistence
│   └── identity.py                 # resolve_actor(source, raw_actor) — cross-source canonical name mapping
└── models/
    ├── activity_event.py           # ActivityEvent Pydantic model
    └── standup.py                  # StandupEntry model

backend/scripts/
├── seed_demo_events.py             # older 3-actor blocker-focused demo seeder (tagged metadata.demo_seed)
└── seed_demo.py                    # 4-actor health-engine demo seeder (tagged metadata.demo_cast="health_v1") — see Demo Data Seeding

backend/tests/                      # pytest — see Backend → Tests above
├── conftest.py                     # loads seed_demo.py's EVENTS as a fixture, without running its main()
├── test_health.py                  # classify_actor() — demo-cast regression + tasks 5/5b edge cases
└── test_blockers.py                # find_blockers() — against a fake Supabase client
```

**Routes:**
- `GET /` → `{"name": "Team Pulse API", "version": "0.1.0"}`
- `GET /health` → service status + supabase_configured flag
- `GET /health/team` → per-actor health classification (HEALTHY/THRASHING/SILENT_STUCK/IDLE) + evidence line (auth required)
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

- `frontend/.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8001` and `NEXT_PUBLIC_API_KEY` (must match backend's `API_KEY` or authed routes 401)
- Shadcn components installed: `card`, `button`, `badge` — add more with `npx shadcn@latest add <component>`
- `framer-motion` and `lucide-react` used for animation/icons throughout

**Design system (redesigned 2026-07-01):** dark theme forced on (`<html class="dark">` in `app/layout.tsx`), gradient-accent palette defined in `app/globals.css` (violet/sky gradients, `.glass`, `.glow-border`, `.gradient-text`, `.bg-grid` utility classes). Built for live pitch/demo settings — see `PITCH.md` (untracked, not in the repo) for the actual pitch script.

**Pages:**
- `/` → landing page (`app/page.tsx`) — animated hero, gradient headline, integrations strip (GitHub/Linear/Notion/Figma/Slack), feature cards
- `/dashboard` → (`app/dashboard/page.tsx`) — team-digest-first live client component:
  - "Generate team digest" button → calls `POST /digest/team` → renders health attention alerts, blocker alerts, team summary card, and per-actor cards
  - **Health attention alert**: if `attention[]` is non-empty, one pulsing card per THRASHING/SILENT_STUCK actor renders at the very top of the digest — above the blocker alert. Amber (`Repeat` icon) for THRASHING phrased as "{actor} — Hard problem, worth a pairing session?"; red/destructive (`AlertOctagon` icon) for SILENT_STUCK phrased as "{actor} — Is this blocked?" — evidence sentence below in both cases. This is the demo's money-shot card.
  - **Blocker alert**: if `blockers[]` is non-empty, a pulsing amber card renders below the health alerts — bold "{title} — no activity in {N} hours"
  - Per-actor cards use `ActorAvatar` (`components/actor-avatar.tsx`) — GitHub avatar image with initials-gradient fallback for non-GitHub actors
  - Per-actor cards also show a `HealthBadge` (`components/health-badge.tsx` — green Healthy / amber Thrashing / red Silent & stuck / gray Idle), `SourceIcons` (`components/source-icons.tsx`) — small GitHub/Linear/Notion/Figma icons from the digest's `sources[]` — and an event-count `Badge`
  - Live "last updated" timestamp next to the API-connected indicator, set whenever a team digest successfully generates
  - "Send to Slack" per card (`POST /slack/deliver`) and for the whole team (`POST /slack/deliver-team`)
  - Collapsible "Add a teammate manually" section preserves the original single-actor lookup flow (`POST /digest/generate`)
  - Live API-connection indicator (pings `GET /health` on mount)
  - Loading / done states, animated with Framer Motion. Error state distinguishes "no activity in last 24h" (calm inbox icon, muted styling — reads as intentional) from a real failure like API-unreachable (distinct red-tinted icon + different copy)

**Frontend dev gotcha (hit 2026-07-13):** if the dashboard ever renders as unstyled black-on-white HTML (no dark theme, no `.glass`/gradient classes, default serif font), it's a stale/corrupted `.next` build cache — usually from multiple stacked `npm run dev` processes writing to the same `.next` folder at once (each port collision spawns another instance instead of failing), sometimes compounded by the machine running low on disk mid-build. Symptoms in the dev server log: `GET /_next/static/css/app/layout.css ... 404` and similar 404s for JS chunks even though the page itself returns 200. Fix: `pkill -f "next dev"`, confirm nothing's still listening on 3000/3001/3002 (`lsof -i :3000 -i :3001 -i :3002 -sTCP:LISTEN`), `rm -rf .next`, then start exactly one `npm run dev`.

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
  received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  dedup_key    TEXT        UNIQUE      -- webhook idempotency key, added 2026-07-22, see Migrations below
);
```

The timestamp column is `received_at` (not `created_at`).

**Migrations:** `backend/migrations/` — plain `.sql` files, applied manually via the Supabase SQL editor (no migration runner wired up). Not auto-applied by the app or by deploys.

- `0001_activity_events_dedup_key.sql` — adds the `dedup_key` column + `UNIQUE` constraint above. **⚠️ Must be run against the live Supabase DB before deploying the webhook idempotency change below (2026-07-22) — without it, `on_conflict="dedup_key"` upserts will fail at the Postgres level** (`there is no unique or exclusion constraint matching the ON CONFLICT specification`), meaning the webhook endpoints would 500 on every delivery until this migration is applied. Existing rows get `dedup_key = NULL`, which is safe — Postgres `UNIQUE` allows unlimited `NULL`s, no backfill needed.
- `0002_job_runs.sql` — creates the `job_runs` table (see Scheduler → Run persistence). **⚠️ Must be run before deploying** — without it, `record_run()`/`get_last_run()` calls fail (caught and logged, won't crash the process), but `/scheduler/status` and `/notion/status` will silently report `None`/empty and the missed-run catch-up check won't work until this migration exists.
- `0003_actor_aliases.sql` — creates the `actor_aliases` table (see Actor Identity Mapping section below). **Safe to defer** — unlike the two above, nothing breaks or degrades before this runs: `resolve_actor()` catches the missing-table error, logs it, and passes every raw actor string through unchanged, exactly like the "no alias configured" case.

**Event sources and types stored:**
| source | event_type values |
|---|---|
| `github` | `pr_opened`, `pr_merged`, `pr_closed`, `commit_pushed` |
| `linear` | `issue_created`, `issue_started`, `issue_completed`, `issue_cancelled`, `issue_updated`, `comment_added` |
| `figma` | `file_comment`, `version_saved` |
| `notion` | `page_created`, `page_edited` |

---

## Actor Identity Mapping (complete, 2026-07-23)

**Core logic:** `backend/app/services/identity.py` → `resolve_actor(source, raw_actor)`

One human can show up under a different handle per source — a GitHub login, a Linear `displayName`, a Figma handle, a Notion display name. `resolve_actor()` maps a `(source, raw_actor)` pair to a canonical person name via the new `actor_aliases` table, called once at ingestion in **all four write paths** — `webhooks/github.py`, `webhooks/linear.py`, `webhooks/figma.py`, and `services/notion.py`'s `sync_notion()` — right before the Supabase write, mutating `event.actor` on the already-constructed `ActivityEvent`(s). `activity_events.actor` stores the canonical name going forward; nothing downstream (`digest.py`, `team_digest.py`, `health.py`, `blockers.py`, `scheduler.py`) needed to change, since they all just group by whatever string is in that column.

**Table:** `actor_aliases (canonical_name, source, source_actor)`, one row per `(source, source_actor)` mapping, unique-indexed on that pair. See `backend/migrations/0003_actor_aliases.sql` for schema + example inserts. No admin UI — managed by hand in the Supabase table editor for now, matching the "concierge, not self-serve" posture `GTM-NOTES.md` already recommends for this stage.

**Safety property (the one that matters most): unmapped actors are never dropped.** An actor with no alias row, an alias lookup that fails outright (table doesn't exist yet, Supabase unreachable), or an empty actor string — all of these pass the raw actor string through completely unchanged. The failure mode is "shows up as two people instead of one" (annoying, visible, fixable by adding an alias), never "this person's activity silently vanished." Verified directly: pointed `get_supabase()` at a function that always raises, and `resolve_actor()` still returned the raw actor string, not an exception.

**Normalization:** matching is case-insensitive and whitespace-trimmed on both sides (`.strip().casefold()`, applied to both the stored `source_actor` and the incoming raw actor at lookup time) — `"Dev Okoye"`, `"dev okoye"`, and `"  DEV OKOYE  "` all resolve the same. Matching is still scoped per-`source` — a GitHub alias never matches a Linear lookup for the same string, consistent with the "no cross-source identity" principle from the THRASHING scope-key fix (Person Health Engine section).

**Caching:** in-memory, 60s TTL (`_CACHE_TTL_SECONDS`), thread-safe via a lock, refreshed lazily on the next `resolve_actor()` call after the TTL expires — not hit on every single webhook delivery. A refresh failure falls back to the last-known-good cache (or empty, before the first successful load) rather than raising. `invalidate_cache()` exists for forcing an immediate reload (not wired to anything yet — no admin endpoint calls it today, but it's there for when one exists).

**Backfill decision: deferred to you, not assumed.** Existing `activity_events` rows (including the demo seed) already contain raw, un-resolved actor strings, and `resolve_actor()` only runs at ingestion — it does not retroactively touch historical rows. Two options, tradeoffs below; **recommendation is (a)**, but this hasn't been implemented — say which you want:
- **(a) One-time backfill script.** Rewrite historical rows' `actor` column in place (preserving the original raw value in `metadata.original_actor` for audit) for any row whose `actor` matches a `source_actor` in `actor_aliases`. Pro: converges old data to the exact same shape as new data — `activity_events.actor` is canonical everywhere, full stop, one mechanism, no query-site changes needed anywhere. Con: not truly "one-time" — needs re-running (idempotent, so safe to just re-run) whenever a new alias is added, to retroactively canonicalize the historical rows that alias now applies to; a destructive rewrite of stored data, even with the original preserved in metadata.
- **(b) Resolve at read time as a fallback.** Leave historical rows raw; apply `resolve_actor()` to rows after fetching, in every service that reads `activity_events`. Pro: non-destructive, and a newly added alias retroactively applies to *all* historical data instantly, no re-run needed. Con: breaks `generate_digest(actor)`'s `.eq("actor", actor)` filter specifically — if `actor` is a canonical name but the stored rows are raw, that filter matches nothing at the DB level, so this option isn't a drop-in — it would need `digest.py.generate_digest()` changed to either resolve canonical→raw aliases first and query with `.in_()`, or fetch broader and filter in Python. Also means permanently running two different resolution mechanisms side by side (ingestion-time for new rows, read-time for old ones) rather than converging to one.

The going-forward architecture is already ingestion-time resolution (per this task's design), which is why (a) is the recommendation — it converges to a single mechanism instead of maintaining two indefinitely. Not implemented pending your choice.

**Verified 2026-07-23**, all through the real webhook handler / `sync_notion()` functions, against a fake Supabase table:
1. Seeded `actor_aliases` with `('Dev Okoye','github','dev-builds')` and `('Dev Okoye','notion','Devansh')`. Sent a real GitHub PR-opened payload for `dev-builds` through `github_webhook()`, and a real Notion sync for a page last-edited by a user resolving to display name `Devansh` through `sync_notion()`. Result: `activity_events` stored both under `actor="Dev Okoye"`; `generate_team_digest()`'s actor-discovery query (`{row["actor"] for row in ...}`) returned exactly `{"Dev Okoye"}`; `classify_team_health()` returned exactly one entry for `"Dev Okoye"` — one person, not two.
2. Sent a GitHub event for `num-err` (no alias configured) — stored, discovered, and classified under `"num-err"` unchanged, alongside `"Dev Okoye"`. Unmapped actor confirmed **not** dropped.
3. Re-ran the actual `seed_demo.py` cast (untouched by this change — the seed script inserts directly, never through ingestion) through `classify_actor()` — still exactly 4 people, all four classifications (Sara/Priya/Marcus `HEALTHY`, Dev `THRASHING`) unchanged.
4. Confirmed the stored `dedup_key` for the `dev-builds` PR event was `"github:pr:acme/pricing-service:42:pr_opened"` — no actor substring in it, unaffected by resolution happening after construction. Replayed the identical payload a second time: row count stayed the same (idempotency from task 3 still holds with identity resolution now sitting in the path).
5. Also confirmed separately: 50 `resolve_actor()` calls within the TTL window produced exactly 1 Supabase query (not 50); `invalidate_cache()` forces a fresh reload; case/whitespace variants (`"DEV-BUILDS"`, `"  dev-builds  "`) all resolved correctly; a same-string lookup on the wrong `source` did **not** match.

---

## GitHub Webhook Integration (complete)

**What's built:**
- `POST /webhooks/github` in `backend/app/routes/webhooks/github.py`
- HMAC-SHA256 signature verification via `X-Hub-Signature-256` (skipped when `GITHUB_WEBHOOK_SECRET` is empty)
- Handles `pull_request` events (opened, closed, merged) and `push` events (one row per commit)
- Normalizes to `ActivityEvent` and batch-**upserts** to Supabase (`on_conflict="dedup_key", ignore_duplicates=True` — see Idempotency below)

**Event normalization rules:**
- `pull_request` / opened → `pr_opened`
- `pull_request` / closed + merged=true → `pr_merged`
- `pull_request` / closed + merged=false → `pr_closed`
- `push` → one `commit_pushed` event per commit in `payload.commits`

**Idempotency (added 2026-07-22):** `dedup_key = f"github:pr:{repo}:{pr_number}:{event_type}"` for PR events, `f"github:commit:{repo}:{sha}"` for commits. A GitHub-retried delivery of the same PR action or the same commit SHA collides on the DB's `UNIQUE(dedup_key)` and is silently dropped (`ON CONFLICT DO NOTHING`) instead of inserting a duplicate row. Requires migration `0001_activity_events_dedup_key.sql` — see Database section.

**Verified:** Real PR events from GitHub (num-err PR #1 on `num-err/team-pulse`) produced 5 rows in `activity_events`.

---

## ngrok / Local Tunnel

ngrok is installed and the authtoken is configured. To expose the backend:

```bash
ngrok http 8001
```

**Currently live** (as of 2026-07-09): a tunnel has been running continuously since 2026-07-07 at `https://enforced-canine-unenvied.ngrok-free.dev` → `localhost:8001`. The GitHub webhook is registered against this exact URL and its last delivery was a real 204 OK on 2026-07-08. If this ngrok process ever restarts, the free-tier subdomain will change and the webhook registration below will need updating to match.

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

**System prompt:** now includes a health-context paragraph (see Person Health Engine section) appended after the base instructions:
> "You are a progress summarization assistant for a software team. Given the following raw activity data for {actor} on {date}, write a 2-4 sentence plain-English summary of what they accomplished. Write in third person. Be specific. Keep it under 100 words. No bullet points.
>
> Context: {actor}'s current status is {health_state} — {health_evidence}. Let the tone reflect this naturally (note momentum if things are moving, or gently flag if they seem stuck spinning on the same thing without progress) — but don't state the status label verbatim or editorialize heavily."

**Response shape:**
```json
{
  "summary": "On 2026-06-29, num-err ...",
  "actor": "num-err",
  "date": "2026-06-29",
  "event_count": 6,
  "sources": ["github", "linear"],
  "health": {"actor": "num-err", "state": "HEALTHY", "evidence": "6 events in the last 3 days, including a ticket moved to Done."}
}
```

**Notes:**
- `anthropic.Anthropic(api_key=get_settings().anthropic_api_key)` — key passed explicitly because uvicorn doesn't auto-load `.env` into `os.environ`
- Model: `claude-haiku-4-5`, `max_tokens=256`
- Returns 404 if no events found for actor in the last 24 hours
- Calls `get_actor_health(actor)` (14-day lookback, separate from the 24h digest query) to build the `health` field and the prompt context — see Person Health Engine section

**Anthropic error handling (added 2026-07-22).** The actual `client.messages.create()` call — used by both `generate_digest()` here and the team-rollup call in `generate_team_digest()` — now goes through `_call_claude()` (`digest.py`), which classifies failures instead of letting them fall through as a raw 500:
- **Transient** (`APIConnectionError` incl. timeouts, `RateLimitError`, `InternalServerError`, `OverloadedError`) → logged as a warning, retried once after a 1.5s backoff, then **503** if still failing.
- **Permanent** (`AuthenticationError`, `BadRequestError`, and everything else under `anthropic.APIError`) → logged as an error, **502** immediately, no retry — retrying a bad API key wastes a second call for no chance of success.

`generate_team_digest()`'s per-actor loop used to do a bare `except HTTPException: pass` around each `generate_digest(actor)` call — meaning a real 502/503 from one actor (not just the benign "no events this window" 404) would silently vanish from the team digest with zero trace. Fixed at the same time: 404s are still skipped silently (that's the intended race-condition path), but any other status now logs `"Skipping {actor} in team digest — {status}: {detail}"` before continuing.

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

**Error handling (broadened 2026-07-22).** `post_digest`/`post_team_digest` used to only catch `SlackApiError` (a real Slack response saying "no"). slack_sdk's `WebClient` re-raises a genuine connection/timeout failure (DNS, refused connection, TLS, socket timeout) as the raw stdlib exception instead of wrapping it — `URLError`, `TimeoutError`, and `ConnectionError` all subclass `OSError`, so both functions now also catch `OSError` and wrap it the same way (`RuntimeError("could not reach Slack: ...")`), which the route layer (`routes/slack.py`) already turned into a 502. Net effect: a Slack outage now returns the same 502 a Slack-side API error does, instead of leaking through as an unhandled 500. Both branches log via `logger.error` before re-raising.

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
- Stores last run result via `record_run()` (`services/job_runs.py`) — visible via `GET /scheduler/status`, survives restart (see Run persistence below)

**Per-actor isolation, verified 2026-07-22** (this loop's `except Exception` was already in place before today, but it's now been actually exercised, not just read): simulated 3 actors where the middle one's `generate_digest()` raises the new `HTTPException(503, ...)` from an Anthropic transient-failure classification (see AI Synthesis Engine section). Result: the other two actors both still got `status: "delivered"` with real Slack timestamps, the failing actor was recorded as `status: "error"` with the 503 detail preserved in `results`, `run_daily_digests()` returned normally instead of raising, and `logger.error("Failed digest for bob: ...")` fired — confirmed present in the log output, not silently swallowed.

**Wired via FastAPI lifespan** (`main.py`) — starts on server boot, shuts down cleanly on exit.

**Config:**
```
DIGEST_CRON_HOUR=9    # UTC (default: 9 AM)
DIGEST_CRON_MINUTE=0
```

**Run persistence + missed-run catch-up (added 2026-07-23).** Both `scheduler.py`'s old `_last_run` and `notion.py`'s old `_last_sync` were in-memory globals that reset to nothing on every process restart — and `routes/notion.py` additionally imported `_last_sync` **by value** (`from app.services.notion import sync_notion, _last_sync`), snapshotting `None` once at import time and never seeing later updates, so `GET /notion/status` reported `None` even mid-process, restart or not. Fixed both together with one shared mechanism:
- **`backend/app/services/job_runs.py`** (new) — `record_run(job_name, ran_at, result)` / `get_last_run(job_name)`, backed by a new `job_runs` Supabase table (not an in-memory variable). `scheduler.py`'s `run_daily_digests()` and `notion.py`'s `sync_notion()` both call `record_run()` at the end; `scheduler.get_last_run()` and the new `notion.get_last_sync()` both call `get_last_run()` with their own job name. **Requires running `backend/migrations/0002_job_runs.sql` against Supabase** — see Database → Migrations.
- **The by-value import bug is fixed structurally, not patched around**: `_last_sync` no longer exists as a module variable to import by value at all — `routes/notion.py` now imports and calls `get_last_sync()`, a real function, same pattern `routes/scheduler.py` already used correctly for `get_last_run()`.
- **Missed-run catch-up**: `catch_up_if_missed()` (`scheduler.py`) runs once at startup (`main.py` lifespan, after the scheduler starts) — if the current time is past today's scheduled `DIGEST_CRON_HOUR:DIGEST_CRON_MINUTE` and no `job_runs` row exists for today, it runs the digest immediately. This is the case `misfire_grace_time` (also added, `MISFIRE_GRACE_SECONDS = 3600` on both cron jobs) can't cover — a full process restart means a brand-new `BackgroundScheduler` with no memory of a tick it never got the chance to register; misfire grace only helps a process that stayed alive but was briefly blocked past its own trigger time. Idempotent by construction: a second same-day restart sees today's run already recorded and does nothing.

**Verified 2026-07-23**, all through the real functions (`catch_up_if_missed()`, `run_daily_digests()`, `get_last_run()`, `sync_notion()`, `routes/notion.py`'s `notion_status()`), against a fake Supabase table that persists across `importlib.reload()` of every involved module (the same restart-simulation technique used for the Notion cursor fix in task 2):
1. Simulated the process being down across the scheduled window (no `job_runs` row for today), then called `catch_up_if_missed()` — the digest ran exactly once (1 `generate_digest` call, 1 Slack post, 1 `job_runs` row).
2. Reloaded every module (full restart simulation) and called `get_last_run()` — returned the real persisted run (`actor_count`, `results`, matching `alice`'s delivery), not `None`.
3. Called `catch_up_if_missed()` again post-restart (simulating a second same-day restart) — today's run was already on record, so it did **not** re-run: still exactly 1 `generate_digest` call and 1 `job_runs` row total, confirming no double-send.
4. Ran `sync_notion()`, then reloaded every module again and called `notion_status()` — returned the real `ran_at`/`events_stored` from before the reload, not `None`.

Also confirmed against the **real** dev environment (real `.env`, real `DIGEST_CRON_HOUR=9`, real clock at 17:49 UTC — genuinely past the scheduled time): booting the actual server correctly triggered `catch_up_if_missed()`, which correctly attempted a real Supabase call (failed only because this sandbox has no network access — a `ConnectError`, not a code defect), and the `try/except` around it in `main.py`'s lifespan caught it cleanly — the server still finished booting and `GET /health` still returned `200`, confirming a DB hiccup during the startup catch-up check can't take the whole app down.

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

**Idempotency (added 2026-07-22):** Issue events key on `f"linear:issue:{data.id}:{event_type}:{updatedAt}"` — including Linear's own `updatedAt` (not just the issue id) is deliberate: it means a true webhook retry (identical `updatedAt`) dedupes, while two genuinely different real updates to the same issue (different `updatedAt`, e.g. `issue_updated` firing twice for two unrelated field changes) still both land as separate rows instead of the second one being wrongly swallowed. Comment events key on the comment's own `id` alone (`f"linear:comment:{data.id}"`) since a comment only ever fires once on create. Same `on_conflict="dedup_key", ignore_duplicates=True` upsert, same migration dependency as GitHub.

**Verified:** Test payload produced `issue_created` row in `activity_events`.

---

## Figma Webhook Integration (built, blocked on paid plan)

**What's built:**
- `POST /webhooks/figma` in `backend/app/routes/webhooks/figma.py`
- Passcode verification (Figma embeds passcode in the JSON body rather than using an HMAC header)
- Handles `FILE_COMMENT` → `file_comment` and `FILE_VERSION_UPDATE` → `version_saved`
- Skips `FILE_UPDATE` (fires on every autosave — too noisy) and `PING`

**Idempotency (added 2026-07-22):** `dedup_key = f"figma:comment:{comment_id}"` / `f"figma:version:{version_id}"` — directly relevant here since Figma is documented to double-fire webhooks; same upsert/migration mechanism as GitHub and Linear.

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
- `backend/app/services/notion.py` → `sync_notion()` — polls `POST /v1/search` sorted by `last_edited_time`, resolves user IDs to display names, deduplicates against `MAX(received_at) WHERE source='notion'` in Supabase (see Restart-safe cursor below)
- `backend/app/routes/notion.py` → `GET /notion/status`, `POST /notion/sync`
- Runs automatically 5 minutes before the daily digest via APScheduler

**Setup:**
1. Go to notion.so/my-integrations → New integration → copy the `secret_...` token
2. Set `NOTION_TOKEN=secret_...` in `.env`
3. In each Notion page/database: click `...` → Connections → connect your integration
4. Pages edited since last sync are stored as `page_created` or `page_edited` events; actor is the Notion user display name

**Verified:** Live sync produced `page_edited` row for actor `Numer Ahmed`.

**Restart-safe cursor (fixed 2026-07-22).** Previously the dedup floor was an in-memory `_last_sync_at` global — reset to `None` on every process restart, which meant the next poll re-walked and re-inserted Notion's *entire* history as duplicate rows (this was the exact landmine the old YC Demo Prep checklist told the operator to avoid by never restarting the backend). `sync_notion()` now calls `_synced_floor()` (`notion.py`), which queries `SELECT received_at ORDER BY received_at DESC LIMIT 1 WHERE source='notion'` from Supabase itself on every run instead of reading any in-memory variable — the floor now lives in the same place the data does, so it survives a restart automatically. There is deliberately no new table or cursor file: the existing `activity_events` rows already carry the watermark.

**Verified 2026-07-22** with a restart-simulating test (fakes the Notion Search API and a Supabase table in memory, `backend/`-relative, not committed — throwaway verification script): synced 3 fake pages (3 rows stored) → `importlib.reload()`'d the whole `notion` module to wipe every module-level variable exactly as a real process restart would → synced again against the same, unedited pages → **0 new rows** (table stayed at 3). Confirmed by reading the diff that the old in-memory-global version would have re-inserted all 3 pages again on this exact sequence (reload wipes `_last_sync_at` back to `None`, so the `since and edited_at <= since` skip check never fires).

**Status reporting fixed 2026-07-23** (was flagged here as a known limitation after task 2, fixed alongside scheduler run persistence — see the Run persistence subsection in the Scheduler section for the full writeup and verification). `sync_notion()`'s status is no longer an in-memory `_last_sync` global at all — it's persisted via `record_run()`/`get_last_run()` (`services/job_runs.py`) to a real `job_runs` table, exposed through a real `get_last_sync()` function instead of `routes/notion.py` importing a variable by value. `GET /notion/status` now reports the real last-sync timestamp, survives restart, same as `GET /scheduler/status`.

---

## Auth (complete)

**Dependency:** `backend/app/deps.py` → `require_api_key`

Uses FastAPI's `APIKeyHeader` (`X-API-Key` header). Applied as a router-level dependency on all non-webhook routes:
- `/digest/generate`, `/slack/deliver`, `/scheduler/*`, `/notion/*`

Webhooks (`/webhooks/github`, `/webhooks/linear`, `/webhooks/figma`) stay unprotected — they use their own HMAC/passcode auth.

**Behavior:**
- `API_KEY` not set in `.env` → auth skipped (open in dev, preserves current behavior)
- `API_KEY` set → header must match exactly, else `401 Unauthorized`

**Generate a key:**
```bash
python -c "import secrets; print('tpulse_' + secrets.token_urlsafe(32))"
```

Add to `backend/.env`:
```
API_KEY=tpulse_<generated>
```

Add to `frontend/.env.local` (if using the dashboard against a keyed backend):
```
NEXT_PUBLIC_API_KEY=tpulse_<generated>
```

---

## Production Deployment (Railway-ready, done 2026-07-22)

**`backend/Procfile`:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
Railway (and Heroku-style platforms) run Procfile commands through a shell, so `$PORT` is substituted from the platform-injected env var at process start — no code needs to read it directly. This is a separate run path from local dev (`--reload --port 8001`); dev keeps using the documented `uvicorn ... --reload` command, production uses the Procfile.

**CORS is now env-driven.** `Settings.cors_origins` (`backend/app/config.py`) is a comma-separated string, default `http://localhost:3000`; `Settings.cors_origins_list` splits/trims it for `main.py`'s `CORSMiddleware`. Set `CORS_ORIGINS=https://your-deployed-frontend.com` (comma-separate multiple origins) in production `.env`/Railway vars.

**Production secret guard.** `validate_production_settings()` (`backend/app/config.py`) runs inside `get_settings()` on first call — i.e. at process boot, before the app serves anything. If `APP_ENV=production` and any of `SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`, `SLACK_BOT_TOKEN`, `API_KEY`, `GITHUB_WEBHOOK_SECRET`, `LINEAR_WEBHOOK_SECRET`, `NOTION_TOKEN` is empty, it raises `RuntimeError` and the process refuses to start, naming exactly which vars are missing. `APP_ENV=development` (the default) skips this entirely — local dev behavior is unchanged, no secrets required. `FIGMA_WEBHOOK_PASSCODE` is deliberately not required — Figma integration is blocked on a paid plan and unreachable regardless.

**Railway env vars needed:** `SUPABASE_URL`, `SUPABASE_KEY`, `APP_ENV=production`, `GITHUB_WEBHOOK_SECRET`, `LINEAR_WEBHOOK_SECRET`, `FIGMA_WEBHOOK_PASSCODE`, `NOTION_TOKEN`, `ANTHROPIC_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_DEFAULT_CHANNEL`, `API_KEY`, `DIGEST_CRON_HOUR`, `DIGEST_CRON_MINUTE`, `CORS_ORIGINS`.

**Verified 2026-07-22:**
- `Settings(app_env='production', <all 8 required fields blank>)` → `validate_production_settings()` raises, naming all 8 missing vars.
- Same with all 8 fields set → does not raise.
- `Settings(app_env='development')` with nothing set → does not raise (dev stays open, unchanged behavior).
- `cors_origins='https://a.com, https://b.com ,https://c.com'` → `cors_origins_list` correctly trims to `['https://a.com', 'https://b.com', 'https://c.com']`.
- Local dev boot unaffected: `uvicorn app.main:app --port 8099` (no `APP_ENV` override) started cleanly, lifespan/scheduler started and shut down without error, `GET /health` returned `200 {"status":"ok",...}`.

**Not yet done:** no actual Railway project has been created/deployed — this makes the codebase deployable, it doesn't deploy it. Also not done: a `railway.json` (Procfile alone is sufficient for Railway's Nixpacks builder, so this is optional, not required).

---

## Multi-Actor Team Digest (complete)

**Service:** `backend/app/services/team_digest.py` → `generate_team_digest()`

1. Queries Supabase for distinct actors active in the last 24h
2. Calls `generate_digest(actor)` for each → collects per-actor summaries
3. Sends all summaries to Claude Haiku → generates a team-level rollup paragraph
4. Returns structured response with both the rollup and per-actor details

**Response shape:**
```json
{
  "date": "2026-06-29",
  "actor_count": 2,
  "event_count": 8,
  "team_summary": "The team made solid progress on...",
  "actors": [
    {"actor": "num-err", "summary": "...", "event_count": 6, "sources": ["github", "linear"], "health": {"state": "HEALTHY", "evidence": "..."}},
    {"actor": "Numer Ahmed", "summary": "...", "event_count": 2, "sources": ["notion"], "health": {"state": "HEALTHY", "evidence": "..."}}
  ],
  "blockers": [
    {"title": "Payment UI Review", "repo": "DESIGN", "actor": "Ada Chen", "hours_since_activity": 52, "url": "https://linear.app/..."}
  ],
  "attention": [
    {"actor": "Dev Okoye", "state": "THRASHING", "evidence": "16 commit/edit events to acme/pricing-service over 3 days, 0 merges, 7 CI failures. ..."}
  ]
}
```

**Endpoints:**
- `POST /digest/team` → returns team digest JSON (auth required)
- `POST /slack/deliver-team[?channel=<id>]` → generate + post to Slack as Block Kit message (auth required)

**Slack format:** Header → team summary → divider → per-actor sections → (if `attention[]` non-empty) divider + "⚠ Attention" section listing each THRASHING/SILENT_STUCK actor with their evidence line → footer with contributor/event count. (Blockers are still not surfaced in Slack — text-only, dashboard-only.)

---

## Blocker Detection (complete)

**Core logic:** `backend/app/services/blockers.py` → `find_blockers(threshold_hours=48)`

Scans `linear`-source events from the last 30 days, groups them by issue (via `metadata.identifier`, falling back to `repo`+`title`), and takes the latest event per issue. If that latest event is `issue_started` and it's older than the threshold, the issue is flagged as a blocker — i.e. someone started it and nothing (comment, completion, cancellation) has happened since.

Wired into `generate_team_digest()` — every `/digest/team` response includes a `blockers` array, independent of the 24h actor-activity window (an issue can be flagged even if the actor who started it has no other activity today).

Frontend renders this as a pulsing amber alert card at the very top of the team digest (`frontend/app/dashboard/page.tsx`) — see Frontend section.

**Scope note:** only Linear `issue_started` is checked. Doesn't (yet) flag stale open GitHub PRs or other "in-progress" signals — could extend the same pattern if needed.

---

## Person Health Engine (complete)

**Core logic:** `backend/app/services/health.py` → `classify_actor()`, `get_actor_health(actor)`, `classify_team_health()`

Built entirely against seeded Supabase data — no webhook or integration code touched. Classifies each actor into one of four states from raw `activity_events`, with a 14-day query lookback per actor:

| State | Rule |
|---|---|
| `HEALTHY` | ≥1 event in the last 72h, and at least one of them is "forward motion" — `pr_merged`, `issue_completed`, or any event tagged `metadata.milestone` |
| `THRASHING` | ≥8 events in 72h on one **eligible** work context (GitHub or Linear only, see below), **zero** forward-motion events *within that context*, **and** an independent struggle signal (CI failure, a PR open 24h+, or a ticket still In Progress in that same context) — high volume alone is never sufficient |
| `SILENT_STUCK` | actor has a Linear ticket whose latest lifecycle event is `issue_started` (still "In Progress"), **and** the actor's most recent event of any kind is 48h+ old |
| `IDLE` | no events in the lookback window (or no recent events and no open in-progress ticket) — rendered neutrally, not as a problem |

**Priority order** when an actor's raw events could satisfy more than one rule's conditions: `SILENT_STUCK` → `THRASHING` → `HEALTHY` → `IDLE`, enforced by early-return `if` checks in that order in `classify_actor()`. This is priority-ordering, not mutual exclusivity of the underlying conditions — an actor's raw events *can* simultaneously satisfy both SILENT_STUCK's condition (an open ticket + 48h+ since their last event of any kind) and THRASHING's condition (8+ same-context events with zero forward motion, if those events happened 48–72h ago, i.e. within the 72h THRASHING window but past the 48h SILENT_STUCK staleness bar). When that happens, SILENT_STUCK wins only because its check runs first and returns immediately — THRASHING is never even evaluated for that actor that call. (Corrected 2026-07-23 — the previous version of this note claimed the two conditions "never overlap... by construction," which overstated the guarantee; what actually prevents double-classification is check order, not the conditions being disjoint.)

**Scope key for THRASHING (fixed 2026-07-23).** Concentration is grouped by `(source, repo)` via `_scope_key()` in `health.py`, not by `repo` alone and not actor-wide. Two reasons:
- **Forward-motion suppression used to be actor-wide, which was a real bug.** The THRASHING check used to gate on `if events_72h and not forward_motion_72h` — *any* forward-motion event anywhere in the actor's 72h window (a trivial merge on a totally unrelated repo) suppressed THRASHING everywhere, even while they were genuinely thrashing on a different repo. Confirmed empirically, not just by reading the code: 12 same-repo events with CI failures and zero merges on repo A, plus one trivial merge on repo B in the same window, classified as HEALTHY under the old logic and THRASHING under the fixed logic, for the identical input. Forward-motion suppression is now computed **within each `(source, repo)` group independently** — a group only escapes THRASHING consideration if forward motion happened in that same group.
- **`(source, repo)` instead of `repo` alone, because `repo` isn't a consistent identity across sources.** It means an actual git repo for GitHub, a team key for Linear (e.g. `ENG`), a file name for Figma, and always the literal string `"notion"` for every Notion event regardless of which page. There's no valid way to treat, say, a Linear team key and a GitHub repo name as "the same work" without inventing a mapping that doesn't exist elsewhere in this codebase (see Identity mapping in What's Next) — so this deliberately scopes within source instead of guessing a cross-source equivalence.
- **An event with no `repo` value gets its own singleton scope** (keyed on the row's own `id`), not lumped into one shared `"unknown"` bucket with every other repo-less event from that actor. Two unrelated pieces of repo-less work look identical without a repo to distinguish them, and silently treating them as "the same work context" would itself be a false signal in either direction — so each one is scoped alone, which in practice means repo-less events can never accumulate into a THRASHING group (they can't reach the 8-event minimum as singletons). Confirmed: 10 unrelated repo-less Notion events for one actor do not collapse into a shared bucket and do not falsely trigger THRASHING.

**Source eligibility + required struggle signal (fixed 2026-07-23, second pass).** The per-scope fix above still had two gaps, both found by investigation before implementing, both confirmed with a real `classify_actor()` call before deciding how to fix them:

- **Figma and Notion can never have a forward-motion event.** `_is_forward_motion()` only recognizes `event_type in {"pr_merged", "issue_completed"}` or `metadata.milestone` — and grepping every normalizer confirms Figma (`file_comment`, `version_saved`) and Notion (`page_created`, `page_edited`) never produce either; `metadata.milestone` is only ever set by the demo seed script, never by real webhook/sync code. So a Notion-only or Figma-only scope group can structurally never show forward motion, meaning any actor with 8+ events in a 72h window in either source alone — a busy documentation week, an active design-review thread — wrongly classified `THRASHING`. Confirmed with a real call: 10 plain `page_edited` events, one actor, one Notion "repo" (`"notion"` is a constant, not a real distinguishing value) → `THRASHING`, evidence `"10 commit/edit events to notion over 3 days, 0 merges."`; 10 Figma events on one file → same wrong result.
- **Raw event count alone was sufficient, with no other signal required.** A GitHub actor with 8+ commits and no merge over 3 days — completely normal mid-feature work — also wrongly classified `THRASHING` under the per-scope fix alone, confirmed the same way.

Fix, chosen deliberately for **precision over recall** — a false `THRASHING` publicly mislabels someone as struggling in the team Slack channel, which is a far more costly mistake than the engine missing a real case:
1. **`_THRASHING_ELIGIBLE_SOURCES = {"github", "linear"}`** — only sources with a defined completion event type are eligible for THRASHING grouping at all. Figma and Notion events are excluded from consideration entirely, not just de-prioritized.
2. **A struggle signal is now required, not just volume.** Within an eligible, zero-forward-motion group: a CI failure (`metadata.ci_status == "failed"`), or an unmerged PR that's been open **24h+** (`STRUGGLE_PR_MIN_AGE_HOURS`, a brand-new PR isn't evidence of anything yet), or a Linear ticket still `issue_started` **in that same `repo`**. `≥8 events` is necessary but no longer sufficient on its own.
3. **The ticket-note check is now scoped to the group's own `repo`, not actor-wide.** This is the same "no invented cross-source identity" principle as the scope key above, applied consistently to the struggle signal too — a stuck Linear ticket on team `DESIGN` shouldn't be able to justify flagging unrelated GitHub thrashing on `acme/some-repo` just because they belong to the same actor. **Side effect, not a regression:** Dev Okoye's evidence string changed as a result — it no longer includes `Ticket "Fix currency rounding bug" still In Progress.`, because his ticket's repo (`ENG`, a Linear team key) never matches his GitHub group's repo (`acme/pricing-service`). He's still correctly `THRASHING` (CI failures + a stale PR are both same-repo, legitimate signals on their own); only the bonus cross-source ticket mention was dropped, because it was never a formally valid link in the first place — see Actor Identity Mapping section, added later the same day. **`PITCH.md` is untracked and wasn't checked** — if it quotes Dev's old evidence string verbatim, that line needs updating before it's used live.

**Verified 2026-07-23**, all through real `classify_actor()` calls: (1) the full `seed_demo.py` cast re-run — Dev still `THRASHING` (new evidence: `"16 commit/edit events to acme/pricing-service over 3 days, 0 merges, 7 CI failures. One PR open 4d, unmerged."`), Sara/Priya/Marcus unchanged at `HEALTHY`; (2) 10 commits/no-merge/no-struggle-signal → `HEALTHY`, not `THRASHING`; (3) 10 Notion-only and 10 Figma-only events → both `HEALTHY`, not `THRASHING`; (4) a dedicated Linear-only-no-GitHub test to answer honestly whether this is now a GitHub-only feature — **it isn't, but it's close**: a Linear-only actor with 8+ events on one team and a ticket that never resolves does classify `THRASHING` (confirmed), but a Linear group has exactly **one** struggle-signal path available (a stuck ticket) versus GitHub's **two** (CI failures or a stale PR) — CI-failure and stale-PR signals are GitHub-only concepts, structurally unavailable to Linear. The same volume of Linear churn where every ticket eventually resolves will never trigger THRASHING, by design.

**Endpoint:** `GET /health/team` (auth required) → `{"actors": [{"actor": ..., "state": ..., "evidence": ...}, ...]}`, sorted by severity.

**Surfaced everywhere:**
- `generate_digest(actor)` calls `get_actor_health(actor)` and folds the state + evidence into the Claude system prompt, and returns it as a `health` field on the digest response (see AI Synthesis Engine section)
- `generate_team_digest()` includes `health` on every actor entry, plus a top-level `attention[]` array of just the THRASHING/SILENT_STUCK actors (see Multi-Actor Team Digest section)
- Dashboard renders a prominent alert card per `attention[]` entry above everything else, plus a `HealthBadge` on every actor card (see Frontend section)
- Slack team digest appends a "⚠ Attention" section listing THRASHING/SILENT_STUCK actors with evidence (see Slack Delivery section)

**Design note:** a Linear ticket can independently trip both `find_blockers()` (ticket-level, 48h since `issue_started`) and this engine's `SILENT_STUCK`/`THRASHING` (person-level) — they're deliberately different lenses on the same raw signal (ticket staleness vs. person activity) and can disagree in an informative way (e.g. a thrashing engineer whose ticket looks "blocked" in Linear but who is actually very active in GitHub). The demo seed script times Dev Okoye's stuck ticket at 40h — under the 48h blocker threshold — specifically so only the THRASHING card fires for him, not a redundant blocker card too.

---

## Demo Data Seeding

Two independent, non-colliding seed scripts — each wipes only its own tagged rows, so running one doesn't clear the other's data.

**`backend/scripts/seed_demo_events.py`** — older 3-actor blocker-focused demo (tags rows `metadata.demo_seed: true`):
- **num-err** — GitHub commit + PR, Linear `issue_started`→`issue_completed`, Figma comment (all inside the 24h window)
- **Numer Ahmed** — two Notion page edits, one Linear comment
- **Ada Chen** — a recent Figma version save (inside 24h window) plus a deliberately stale Linear `issue_started` for "Payment UI Review" backdated 52 hours, to exercise the blocker alert

```bash
cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo_events.py
```

**`backend/scripts/seed_demo.py`** — 4-actor health-engine demo, two weeks of timestamp-relative-to-now events (tags rows `metadata.demo_cast: "health_v1"`):
- **Sara Kim** (designer) — Figma comments + a "ready for handoff" milestone 2 days ago → `HEALTHY`
- **Priya Sharma** (PM) — Notion roadmap/synthesis edits, a Linear ticket created + one moved to Done yesterday → `HEALTHY`
- **Marcus Webb** (engineer) — steady commits, two PRs merged inside the 72h window, a Linear ticket closed → `HEALTHY`
- **Dev Okoye** (engineer) — healthy first week (old, outside every scoring window), then 16 commits over the last 3 days to `acme/pricing-service` ("attempt 2", "revert", "try Banker's rounding", ...), 7 tagged `ci_status: failed`, one PR opened 4 days ago never merged, Linear ticket "Fix currency rounding bug" started 40h ago and never moved → `THRASHING`

```bash
cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo.py
```

Verified 2026-07-12: `GET /health/team` returns exactly the states above (Dev Okoye = THRASHING with evidence `"16 commit/edit events to acme/pricing-service over 3 days, 0 merges, 7 CI failures. One PR open 4d, unmerged. Ticket \"Fix currency rounding bug\" still In Progress."`), `POST /digest/team` includes `attention: [{"actor": "Dev Okoye", ...}]` and each actor's AI-written summary reflects their health state in tone without stating the label, and the Slack block payload (dry-run tested, not actually posted) includes the "⚠ Attention" section. Dashboard visually confirmed 2026-07-13 (dark theme, alert cards, health badges all rendering correctly after the `.next` cache fix above).

**Live-narration pitch script** for this exact seeded cast (Sara Kim / Priya Sharma / Marcus Webb / Dev Okoye, money-shot on Dev's THRASHING card) is finalized in `PITCH.md` — cross-checked line-by-line against the real seeded evidence so the spoken numbers match what's on screen (Dev's commits failed CI **7** times, not a rounder-sounding guess — get this wrong live and it visibly contradicts the evidence line on the alert card while you're saying it).

---

## What's Next (not yet built)

| Area | Detail |
|---|---|
| Slack DMs | Send each actor their own digest as a DM (needs `users:read` + `im:write` scopes) |
| Figma (unblocked) | Upgrade to Figma Professional plan to activate the already-built `/webhooks/figma` endpoint — see Figma Webhook Integration section above for exact activation steps |
| Actor identity mapping backfill | Ingestion-time resolution is done (see Actor Identity Mapping section); historical rows aren't retroactively canonicalized. **Decided:** option (a), one-time script, to be built after the test suite — deferred because nothing currently in `activity_events` needs it (seed uses canonical names already, real events are still one-handle-per-source) |
| Blocker detection scope | Only checks Linear `issue_started` staleness — doesn't flag stale open GitHub PRs or other in-progress signals yet |
| Actual Railway deployment | Codebase is now deployable (Procfile, env-driven CORS, prod secret guard — see Production Deployment section) but no Railway project has actually been created/deployed yet |
| Test coverage — critical logic with zero tests | The task-8 suite covers `classify_actor()` and `find_blockers()` only, by explicit scope. Still completely untested: all 3 webhook normalizers (`_normalize_pr`/`_normalize_push`/`_normalize_issue`/`_normalize_comment`/Figma's normalizers) — the event-shape parsing that would break silently on a GitHub/Linear/Figma payload schema change; `resolve_actor()` / the whole identity mapping module (task 7) — no test exercises the cache, TTL, normalization, or fallback-on-failure behavior, only the manual verification during that task; `_call_claude()`'s retry/classification logic (task 4) — transient-vs-permanent Anthropic error handling; the Slack `OSError`-catching broaden (task 4); `catch_up_if_missed()` / `job_runs.py` persistence (task 6) — the restart/no-double-fire logic; the Notion sync cursor (`_synced_floor()`, task 2); webhook idempotency / `dedup_key` construction (task 3); `get_actor_health()` and `classify_team_health()` themselves (only the pure `classify_actor()` they wrap is tested — the Supabase query construction and grouping around it is not). All of the above were verified manually, once, during their respective tasks (see each section's "Verified" writeup) — none of that is guarded by an automated test that would catch a future regression. |

---

## Git

- Remote: `https://github.com/num-err/team-pulse`
- Branch: `main`
