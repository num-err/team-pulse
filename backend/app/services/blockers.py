from datetime import datetime, timedelta, timezone

from app.integrations.supabase_client import get_supabase

BLOCKER_THRESHOLD_HOURS = 48
_LOOKBACK_DAYS = 30


def find_blockers(threshold_hours: float = BLOCKER_THRESHOLD_HOURS) -> list[dict]:
    """Flag Linear issues whose most recent activity is 'started' and stale.

    An issue that was started but has seen no further event (comment,
    completion, cancellation) in over `threshold_hours` reads as blocked.
    """
    supabase = get_supabase()
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)

    result = (
        supabase.table("activity_events")
        .select("*")
        .eq("source", "linear")
        .gte("received_at", since.isoformat())
        .order("received_at")
        .execute()
    )

    latest_by_issue: dict[str, dict] = {}
    for row in result.data or []:
        metadata = row.get("metadata") or {}
        key = (
            metadata.get("identifier")
            or metadata.get("issue_identifier")
            or f"{row.get('repo')}::{row.get('title')}"
        )
        latest_by_issue[key] = row  # ascending order, so last write is latest

    now = datetime.now(timezone.utc)
    blockers = []
    for row in latest_by_issue.values():
        if row["event_type"] != "issue_started":
            continue
        received_at = datetime.fromisoformat(row["received_at"].replace("Z", "+00:00"))
        hours_since = (now - received_at).total_seconds() / 3600
        if hours_since >= threshold_hours:
            blockers.append({
                "title": row.get("title") or "Untitled issue",
                "repo": row.get("repo"),
                "actor": row.get("actor"),
                "hours_since_activity": round(hours_since),
                "url": row.get("url"),
            })

    blockers.sort(key=lambda b: b["hours_since_activity"], reverse=True)
    return blockers
