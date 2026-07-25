-- Cross-source actor identity mapping. Lets one human who shows up under a
-- different handle per source (GitHub login, Linear displayName, Figma
-- handle, Notion display name) be stored under one canonical name in
-- activity_events going forward, instead of appearing as separate people
-- in every digest/health/blocker view.
--
-- Run this once, directly in the Supabase SQL editor (or via `psql`) — it
-- is not applied automatically by the app. Until this table exists,
-- resolve_actor() (backend/app/services/identity.py) fails its lookup,
-- logs it, and falls back to passing the raw actor string through
-- unchanged — ingestion is never blocked by this migration being pending.

CREATE TABLE IF NOT EXISTS actor_aliases (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name TEXT        NOT NULL,   -- the name activity_events.actor gets rewritten to
  source         TEXT        NOT NULL,   -- 'github' | 'linear' | 'figma' | 'notion'
  source_actor   TEXT        NOT NULL,   -- the raw actor string that source produces (exact casing as seen)
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One mapping per (source, source_actor) — a given raw handle on a given
-- source maps to exactly one canonical person. Matching is case-insensitive
-- and whitespace-trimmed in application code (resolve_actor() casefolds
-- and strips both sides), not enforced here at the DB level — this keeps
-- the constraint itself simple (no citext extension, no functional index)
-- while the app-level normalization is what actually needs to be
-- case-insensitive to match webhook payload quirks.
CREATE UNIQUE INDEX IF NOT EXISTS actor_aliases_source_actor_unique
  ON actor_aliases (source, source_actor);

-- Example rows (adjust to your real team before running, or insert via
-- the Supabase table editor instead):
-- INSERT INTO actor_aliases (canonical_name, source, source_actor) VALUES
--   ('Dev Okoye', 'github', 'dev-builds'),
--   ('Dev Okoye', 'notion', 'Devansh');

-- Verify afterwards:
--   SELECT canonical_name, source, source_actor FROM actor_aliases ORDER BY canonical_name;
