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


def record_run(job_name: str, ran_at: datetime, result: dict, workspace_id: str | None = None) -> bool:
    """Persist that `job_name` ran at `ran_at` (for `workspace_id`, or globally if None).

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
            "workspace_id": workspace_id,
        }).execute()
        return True
    except Exception:
        logger.exception("Failed to persist run record for job=%s", job_name)
        return False


def get_last_run(job_name: str, workspace_id: str | None = None) -> dict | None:
    """Most recent run record for `job_name` (in `workspace_id`, or global if
    None), or None if it has never run."""
    try:
        supabase = get_supabase()
        query = supabase.table("job_runs").select("ran_at, result").eq("job_name", job_name)
        query = query.eq("workspace_id", workspace_id) if workspace_id else query.is_("workspace_id", "null")
        result = (
            query
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


def list_runs_since(job_name: str, workspace_id: str, since: datetime) -> list[dict] | None:
    """Run records for `job_name` in `workspace_id` since `since`, oldest first.

    Returns None (not []) if the lookup itself fails, so callers that use
    this to avoid duplicate work can fail closed instead of assuming
    "never ran" and repeating it.
    """
    try:
        rows = (
            get_supabase()
            .table("job_runs")
            .select("ran_at, result")
            .eq("job_name", job_name)
            .eq("workspace_id", workspace_id)
            .gte("ran_at", since.isoformat())
            .order("ran_at")
            .execute()
            .data
            or []
        )
        return [{"ran_at": r["ran_at"], **(r.get("result") or {})} for r in rows]
    except Exception:
        logger.exception("Failed to list runs for job=%s workspace=%s", job_name, workspace_id)
        return None
