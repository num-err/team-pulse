# TeamPulse

**Zero-input async standups.** TeamPulse turns the activity a team already produces in GitHub, Linear, Figma, and Notion into a daily AI-written standup digest in Slack — no forms, no "what did you do yesterday?" bot nags.

It also flags people who look stuck before they say so: someone committing over and over with failing CI and no merges, or a ticket that's sat "In Progress" for days with no activity.

### 🔗 [Live demo →](https://num-err.github.io/team-pulse/dashboard/)

Click **Generate team digest** to see a sample four-person team, including a THRASHING alert. The demo runs on built-in sample data (no backend), so Slack delivery is simulated.

**Stack:** FastAPI · Python 3.13 · PostgreSQL (Supabase) · Anthropic API (Claude Haiku) · Slack SDK · APScheduler · Next.js 14 · TypeScript · Tailwind · shadcn/ui

---

## How it works

```
GitHub ──webhook (HMAC)──┐
Linear ──webhook (HMAC)──┤
Figma  ──webhook (passcode)┼──► normalize ──► resolve identity ──► upsert (dedup_key) ──► activity_events (Postgres)
Notion ──polling (cursor)─┘                                                                     │
                                                                                                ▼
                                        health engine + blocker detection ◄─── daily scheduler (APScheduler)
                                                                                                │
                                                     Claude Haiku: per-person + team summary ◄──┘
                                                                                                │
                                                          Slack Block Kit digest  +  Next.js dashboard
```

1. **Ingest.** Each source is normalized into one `ActivityEvent` shape (`source`, `event_type`, `actor`, `repo`, `title`, `url`, `metadata`).
2. **Deduplicate.** Every event gets a natural `dedup_key` (e.g. `github:commit:{repo}:{sha}`) backed by a `UNIQUE` constraint, so retried or double-fired webhooks are dropped instead of double-counted.
3. **Resolve identity.** One person can be `dev-builds` on GitHub and `Devansh` in Notion. An `actor_aliases` table maps each handle to one canonical name. Unmapped people are never dropped — worst case they show up as two people.
4. **Classify health.** Each person is labeled `HEALTHY`, `THRASHING`, `SILENT_STUCK`, or `IDLE` from the last 14 days of events.
5. **Summarize and deliver.** Claude Haiku writes a short summary per person plus a team rollup; it's posted to Slack and shown on the dashboard.

## Key features

**Exactly-once ingestion.** Webhooks are signature-verified (HMAC-SHA256 for GitHub and Linear, passcode for Figma) and written with `ON CONFLICT DO NOTHING` upserts. Notion has no free-tier webhooks, so it's polled with a cursor derived from the database, which survives restarts.

**Team-health engine.** `THRASHING` requires more than raw volume: 8+ events on one GitHub repo or Linear team in 72 hours, zero merges or completed tickets in that same scope, *and* an independent struggle signal (a CI failure, a PR open 24h+, or a ticket stuck In Progress). It's tuned for precision over recall, because falsely labeling someone as struggling in a team channel is worse than missing a case.

**Blocker detection.** Linear issues that were started but have had no comment, completion, or cancellation for 48h+ are surfaced at the top of the digest.

**Fault-tolerant scheduling.** Daily runs are recorded in a `job_runs` table. If the server was down at the scheduled time, a startup catch-up check runs the missed digest — without re-sending one that already went out. One person's failure (e.g. an Anthropic timeout) is isolated and logged; everyone else still gets their digest.

**Error handling.** Transient Anthropic errors (timeouts, rate limits, overload) are retried once then return 503; permanent ones (bad key, bad request) return 502 immediately. Slack outages return a clean 502 instead of an unhandled 500.

## API

All non-webhook routes require an `X-API-Key` header when `API_KEY` is set.

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/webhooks/github` · `/webhooks/linear` · `/webhooks/figma` | Ingest events |
| `POST` | `/digest/generate?actor=…` | One person's 24h summary |
| `POST` | `/digest/team` | Team rollup + per-person summaries + blockers |
| `POST` | `/slack/deliver` · `/slack/deliver-team` | Generate and post to Slack |
| `GET` | `/health/team` | Per-person health classification |
| `GET` | `/health` | Liveness check |
| `GET` / `POST` | `/scheduler/status` · `/scheduler/run-now` | Inspect or trigger the daily job |
| `GET` / `POST` | `/notion/status` · `/notion/sync` | Inspect or trigger Notion polling |

Interactive docs are at `/docs` when the backend is running.

## Running locally

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in Supabase, Anthropic, Slack, and webhook secrets
uvicorn app.main:app --reload --port 8001
```

Apply the SQL files in `backend/migrations/` to your Supabase project (in order) before sending webhooks.

**Frontend**

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8001
npm run dev
```

The dashboard is at `http://localhost:3000/dashboard`.

**Demo data** — to see the dashboard without wiring up real integrations:

```bash
cd backend && PYTHONPATH=. python scripts/seed_demo.py
```

## Tests

```bash
cd backend && pytest
```

20 tests cover the health classifier (including the false-positive cases above: Notion/Figma-only volume, commits without a struggle signal, activity on unrelated repos) and blocker detection. They run fully offline — no network or live database.

## Project layout

```
backend/
  app/
    routes/        HTTP endpoints (webhooks/, digest, slack, scheduler, notion)
    services/      digest, team_digest, health, blockers, identity, scheduler, job_runs, slack, notion
    models/        Pydantic models (ActivityEvent, digest responses)
  migrations/      SQL migrations (dedup_key, job_runs, actor_aliases)
  scripts/         demo data seeding
  tests/           pytest suite
frontend/
  app/dashboard/   team digest, health alerts, blocker card
  components/      UI components (shadcn/ui)
```

## Status and roadmap

Working end to end: GitHub, Linear, and Notion ingestion → AI digest → Slack → daily scheduler, plus the dashboard. The Figma endpoint is built but needs a paid Figma plan to receive webhooks.

Next up: per-person Slack DMs, stale-PR blocker detection, and tests for the webhook normalizers and identity mapping.
