-- Webhook idempotency: adds a per-source natural dedup key column and a
-- unique constraint on it, so a retried/double-fired webhook delivery
-- (GitHub redelivery, Linear retry, Figma double-fire) can't insert a
-- duplicate row even under concurrent deliveries.
--
-- Run this once, directly in the Supabase SQL editor (or via `psql`) —
-- it is not applied automatically by the app. Safe to run on the live
-- table: existing rows get dedup_key = NULL, and Postgres unique
-- constraints allow any number of NULLs (they don't collide with each
-- other or with anything else), so no backfill is required and nothing
-- about existing data changes.
--
-- After this runs, backend/app/routes/webhooks/{github,linear,figma}.py
-- upsert with on_conflict="dedup_key", ignore_duplicates=True — i.e.
-- INSERT ... ON CONFLICT (dedup_key) DO NOTHING at the Postgres level.

ALTER TABLE activity_events
  ADD COLUMN IF NOT EXISTS dedup_key TEXT;

ALTER TABLE activity_events
  ADD CONSTRAINT activity_events_dedup_key_unique UNIQUE (dedup_key);

-- Verify afterwards:
--   SELECT conname, contype FROM pg_constraint WHERE conrelid = 'activity_events'::regclass;
--   -- should list activity_events_dedup_key_unique with contype = 'u'
