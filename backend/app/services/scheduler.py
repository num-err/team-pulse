import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.integrations.supabase_client import get_supabase
from app.services.digest import generate_digest
from app.services.job_runs import get_last_run as _get_last_run_record
from app.services.job_runs import record_run
from app.services.slack import post_digest

logger = logging.getLogger(__name__)

JOB_NAME = "daily_digest"

# APScheduler's own grace window for a job whose trigger time it missed
# (e.g. the event loop was busy) while the process stayed up. This does NOT
# cover a full process restart spanning the scheduled time — a brand new
# BackgroundScheduler has no memory of a tick it never got to register.
# That case is handled by catch_up_if_missed() at startup instead.
MISFIRE_GRACE_SECONDS = 3600


def get_last_run() -> dict | None:
    return _get_last_run_record(JOB_NAME)


def run_daily_digests() -> dict:
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

    run_record = {
        "ran_at": started_at.isoformat(),
        "actor_count": len(actors),
        "results": results,
    }
    record_run(JOB_NAME, started_at, {"actor_count": len(actors), "results": results})
    return run_record


def catch_up_if_missed() -> None:
    """Run the daily digest now if today's scheduled run hasn't happened yet.

    Covers the case a full process restart leaves uncovered: if the process
    was down across the scheduled cron time, the new BackgroundScheduler's
    next fire is tomorrow, and today's digest would otherwise simply never
    happen. Called once at startup (see main.py lifespan). Idempotent within
    the same day — if a run already exists for today (whether from the cron
    trigger or an earlier catch-up this same process lifetime), does nothing,
    so restarting twice in one day after the scheduled time doesn't double-send.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    scheduled_today = now.replace(
        hour=settings.digest_cron_hour, minute=settings.digest_cron_minute, second=0, microsecond=0
    )
    if now < scheduled_today:
        return  # today's scheduled time hasn't arrived yet — the normal cron trigger will handle it

    last = get_last_run()
    if last:
        last_ran_at = datetime.fromisoformat(last["ran_at"].replace("Z", "+00:00"))
        if last_ran_at.date() == now.date():
            logger.info("Today's daily digest already ran at %s — no catch-up needed.", last["ran_at"])
            return

    logger.warning(
        "No daily digest run recorded for today as of %s (past the %02d:%02d UTC scheduled time) — "
        "process was likely down across the window. Catching up now.",
        now.isoformat(), settings.digest_cron_hour, settings.digest_cron_minute,
    )
    run_daily_digests()
