-- Multi-tenancy: workspaces, membership, per-workspace integrations, and a
-- workspace_id on every data table.
--
-- Requires 0000-0003 first. Written for a FRESH project (the original
-- single-team Supabase project was shut down): it makes workspace_id
-- NOT NULL, which fails if activity_events / actor_aliases already contain
-- rows. On a project with old rows, either delete them first or create a
-- workspace and backfill workspace_id before the SET NOT NULL statements.
--
-- Auth: users live in Supabase Auth (auth.users). The backend talks to the
-- database with the service-role key and enforces membership itself; RLS is
-- enabled on every table below with NO policies, so the public anon key
-- (which the frontend holds for sign-in) can read and write nothing.

-- ---------------------------------------------------------------- tables

CREATE TABLE IF NOT EXISTS workspaces (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name           TEXT        NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 80),
  timezone       TEXT        NOT NULL DEFAULT 'UTC',     -- IANA name, e.g. 'America/New_York'
  digest_hour    SMALLINT    NOT NULL DEFAULT 9 CHECK (digest_hour BETWEEN 0 AND 23),
  digest_minute  SMALLINT    NOT NULL DEFAULT 0 CHECK (digest_minute BETWEEN 0 AND 59),
  created_by     UUID        REFERENCES auth.users (id) ON DELETE SET NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspace_members (
  workspace_id  UUID        NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
  user_id       UUID        NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  role          TEXT        NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id)
);
CREATE INDEX IF NOT EXISTS workspace_members_user_idx ON workspace_members (user_id);

-- One row per connected tool. `credentials` holds secrets (webhook signing
-- secrets, bot/API tokens) and is never returned by the API; `settings`
-- holds non-secret config (e.g. the Slack channel).
CREATE TABLE IF NOT EXISTS workspace_integrations (
  workspace_id  UUID        NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
  provider      TEXT        NOT NULL CHECK (provider IN ('github', 'linear', 'figma', 'notion', 'slack')),
  credentials   JSONB       NOT NULL DEFAULT '{}'::jsonb,
  settings      JSONB       NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, provider)
);

-- -------------------------------------------------- scope existing tables

-- activity_events: every event belongs to exactly one workspace.
ALTER TABLE activity_events
  ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces (id) ON DELETE CASCADE;
ALTER TABLE activity_events ALTER COLUMN workspace_id SET NOT NULL;

-- Dedup keys are only unique within a workspace: two teams can legitimately
-- receive the same public commit SHA.
ALTER TABLE activity_events DROP CONSTRAINT IF EXISTS activity_events_dedup_key_unique;
ALTER TABLE activity_events
  ADD CONSTRAINT activity_events_workspace_dedup_key_unique UNIQUE (workspace_id, dedup_key);

CREATE INDEX IF NOT EXISTS activity_events_workspace_received_idx
  ON activity_events (workspace_id, received_at DESC);
CREATE INDEX IF NOT EXISTS activity_events_workspace_actor_received_idx
  ON activity_events (workspace_id, actor, received_at DESC);

-- actor_aliases: identity mappings are per workspace.
ALTER TABLE actor_aliases
  ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces (id) ON DELETE CASCADE;
ALTER TABLE actor_aliases ALTER COLUMN workspace_id SET NOT NULL;
DROP INDEX IF EXISTS actor_aliases_source_actor_unique;
CREATE UNIQUE INDEX IF NOT EXISTS actor_aliases_workspace_source_actor_unique
  ON actor_aliases (workspace_id, source, source_actor);

-- job_runs: nullable — NULL means a global (not per-workspace) job.
ALTER TABLE job_runs
  ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces (id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS job_runs_workspace_job_ran_idx
  ON job_runs (workspace_id, job_name, ran_at DESC);

-- --------------------------------------------------------------------- RLS

ALTER TABLE workspaces              ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members       ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_integrations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_events         ENABLE ROW LEVEL SECURITY;
ALTER TABLE actor_aliases           ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_runs                ENABLE ROW LEVEL SECURITY;

-- Verify afterwards:
--   SELECT tablename, rowsecurity FROM pg_tables
--   WHERE schemaname = 'public' ORDER BY tablename;   -- all should be true
