import logging
from datetime import datetime, timedelta, timezone

from app.integrations.supabase_client import get_supabase
from app.services.digest import generate_digest
from app.services.slack import post_digest

logger = logging.getLogger(__name__)

_last_run: dict | None = None


def get_last_run() -> dict | None:
    return _last_run


def run_daily_digests() -> dict:
    global _last_run

    started_at = datetime.now(timezone.utc)
    logger.info("Daily digest job started at %s", started_at.isoformat())

    since = started_at - timedelta(hours=24)
    supabase = get_supabase()
    result = (
        supabase.table("activity_events")
        .select("actor")
        .gte("received_at", since.isoformat())
        .execute()
    )

    actors = list({row["actor"] for row in (result.data or [])})
    logger.info("Found %d active actor(s): %s", len(actors), actors)

    results = []
    for actor in actors:
        try:
            digest = generate_digest(actor)
            ts = post_digest(digest)
            results.append({"actor": actor, "status": "delivered", "slack_ts": ts})
            logger.info("Delivered digest for %s", actor)
        except Exception as exc:
            results.append({"actor": actor, "status": "error", "error": str(exc)})
            logger.error("Failed digest for %s: %s", actor, exc)

    _last_run = {
        "ran_at": started_at.isoformat(),
        "actor_count": len(actors),
        "results": results,
    }
    return _last_run
