-- Scheduler + Notion sync run persistence: replaces two in-memory globals
-- (scheduler.py's old _last_run, notion.py's old _last_sync) that reset to
-- nothing on every process restart with a real table, so GET /scheduler/status
-- and GET /notion/status report accurate "last ran" info even after a
-- redeploy, and so the daily digest job can tell at startup whether today's
-- run already happened (see catch_up_if_missed() in scheduler.py).
--
-- Run this once, directly in the Supabase SQL editor (or via `psql`) — it is
-- not applied automatically by the app.

CREATE TABLE IF NOT EXISTS job_runs (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name    TEXT        NOT NULL,   -- 'daily_digest' | 'notion_sync'
  ran_at      TIMESTAMPTZ NOT NULL,
  result      JSONB       NOT NULL,   -- job-specific summary:
                                       --   daily_digest -> {"actor_count": N, "results": [...]}
                                       --   notion_sync  -> {"events_stored": N}
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS job_runs_job_name_ran_at_idx ON job_runs (job_name, ran_at DESC);

-- Verify afterwards:
--   SELECT job_name, ran_at, result FROM job_runs ORDER BY ran_at DESC LIMIT 5;
