"""Shared persistence for scheduled-job run records.

Used by both the daily digest scheduler and the Notion sync job so their
"last ran at" status survives a process restart, instead of living only in
an in-memory variable that resets on every restart — and instead of a route
importing that variable by value (which snapshots it once at import time and
never sees later updates; see the notion.py fix this replaces).
"""
import logging
from datetime import datetime

from app.integrations.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def record_run(job_name: str, ran_at: datetime, result: dict) -> None:
    """Persist that `job_name` ran at `ran_at` with the given result summary.

    Best-effort: a persistence failure is logged, not raised — the job's own
    work (digests delivered, Notion events stored) already happened and must
    not be treated as failed just because the status record couldn't be written.
    """
    try:
        supabase = get_supabase()
        supabase.table("job_runs").insert({
            "job_name": job_name,
            "ran_at": ran_at.isoformat(),
            "result": result,
        }).execute()
    except Exception:
        logger.exception("Failed to persist run record for job=%s", job_name)


def get_last_run(job_name: str) -> dict | None:
    """Most recent run record for `job_name`, or None if it has never run
    (or hasn't run since this table existed)."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("job_runs")
            .select("ran_at, result")
            .eq("job_name", job_name)
            .order("ran_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        row = rows[0]
        return {"ran_at": row["ran_at"], **row["result"]}
    except Exception:
        logger.exception("Failed to fetch last run for job=%s", job_name)
        return None
