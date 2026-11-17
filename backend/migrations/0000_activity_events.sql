-- Baseline schema: the original activity_events table.
--
-- This table was first created by hand in the Supabase dashboard and only
-- documented in CLAUDE.md; this file makes a fresh project reproducible
-- from the repo alone. Run migrations in order (0000, 0001, ...) in the
-- Supabase SQL editor. Safe to re-run on a project that already has it.

CREATE TABLE IF NOT EXISTS activity_events (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  source       TEXT        NOT NULL,   -- 'github' | 'linear' | 'figma' | 'notion'
  event_type   TEXT        NOT NULL,   -- e.g. 'pr_merged', 'issue_started', 'page_edited'
  actor        TEXT        NOT NULL,   -- canonical person name (see actor_aliases)
  repo         TEXT        NOT NULL,   -- repo / team key / file / 'notion'
  title        TEXT,
  url          TEXT,
  metadata     JSONB,
  received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
