"""Daily digest scheduling, per workspace.

A single interval job (every SCHEDULER_TICK_MINUTES, plus once at startup)
asks each workspace "are you due?". A workspace is due once its local
clock — in its own timezone — passes its configured digest time, until a
run for that local date is on record. That one rule covers normal
scheduling, per-team timezones, and catching up after the process was down
across the scheduled time, without per-workspace cron jobs to keep in sync.

Double-post safety (a team getting the same digest twice is the failure
that matters most here):
- every attempt is recorded in job_runs before the next tick looks;
- if run history can't be read, the workspace is skipped (fail closed);
- an in-process memo also remembers today's deliveries, in case recording
  a successful delivery fails.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from threading import Lock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from app.services.job_runs import get_last_run as _get_last_run_record
from app.services.job_runs import list_runs_since, record_run
from app.services.notion import notion_token_for, sync_notion
from app.services.slack import SlackNotConfigured, post_team_digest, slack_destination
from app.services.team_digest import generate_team_digest
from app.services.workspaces import list_all_workspaces

logger = logging.getLogger(__name__)

JOB_NAME = "daily_digest"

# A run with one of these statuses settles the day; anything else (an AI or
# Slack outage) is retried on later ticks, up to MAX_ATTEMPTS_PER_DAY.
TERMINAL_STATUSES = {"delivered", "no_activity", "not_configured"}
MAX_ATTEMPTS_PER_DAY = 3

_delivered_memo: set[tuple[str, date]] = set()
_memo_lock = Lock()


def get_last_run(workspace_id: str) -> dict | None:
    return _get_last_run_record(JOB_NAME, workspace_id)


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def local_date(workspace: dict, at_utc: datetime) -> date:
    return at_utc.astimezone(_zone(workspace.get("timezone"))).date()


def is_due(workspace: dict, now_utc: datetime, recent_runs: list[dict]) -> bool:
    """Pure decision: should this workspace get its digest now?

    `recent_runs` is the workspace's job_runs history covering at least the
    last ~2 days (any extra is ignored), each with `ran_at` and `status`.
    """
    tz = _zone(workspace.get("timezone"))
    local_now = now_utc.astimezone(tz)
    scheduled = local_now.replace(
        hour=int(workspace.get("digest_hour", 9)),
        minute=int(workspace.get("digest_minute", 0)),
        second=0,
        microsecond=0,
    )
    if local_now < scheduled:
        return False

    today = local_now.date()
    todays = [
        r for r in recent_runs
        if datetime.fromisoformat(str(r["ran_at"]).replace("Z", "+00:00")).astimezone(tz).date() == today
    ]
    if any(r.get("status") in TERMINAL_STATUSES for r in todays):
        return False
    return len(todays) < MAX_ATTEMPTS_PER_DAY


def run_workspace_digest(workspace_id: str, workspace: dict | None = None) -> dict:
    """Generate the team digest for one workspace and post it to Slack.

    Always records the attempt (with its status) in job_runs. Used both by
    the scheduler and by the manual "run now" route.
    """
    started_at = datetime.now(timezone.utc)

    if notion_token_for(workspace_id):
        try:
            sync_notion(workspace_id)
        except Exception:
            logger.exception("Notion sync failed for workspace %s — digesting without fresh Notion data", workspace_id)

    result: dict
    try:
        digest = generate_team_digest(workspace_id)
        dest = slack_destination(workspace_id)
        ts = post_team_digest(digest, dest)
        result = {
            "status": "delivered",
            "slack_ts": ts,
            "actor_count": digest["actor_count"],
            "event_count": digest["event_count"],
        }
        if workspace:
            with _memo_lock:
                _delivered_memo.add((workspace_id, local_date(workspace, started_at)))
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            result = {"status": "no_activity"}
        else:
            result = {"status": "error", "error": str(exc.detail)}
            logger.error("Digest failed for workspace %s: %s", workspace_id, exc.detail)
    except SlackNotConfigured as exc:
        result = {"status": "not_configured", "error": str(exc)}
    except Exception as exc:  # Slack outage, unexpected bug — retried on a later tick
        result = {"status": "error", "error": str(exc)}
        logger.exception("Digest failed for workspace %s", workspace_id)

    record_run(JOB_NAME, started_at, result, workspace_id)
    return {"ran_at": started_at.isoformat(), **result}


def run_due_workspaces(now_utc: datetime | None = None) -> list[dict]:
    """Scheduler tick: run the digest for every workspace that is due."""
    now_utc = now_utc or datetime.now(timezone.utc)
    try:
        workspaces = list_all_workspaces()
    except Exception:
        logger.exception("Scheduler tick: could not list workspaces")
        return []

    outcomes = []
    for ws in workspaces:
        ws_id = str(ws["id"])
        with _memo_lock:
            if (ws_id, local_date(ws, now_utc)) in _delivered_memo:
                continue
        runs = list_runs_since(JOB_NAME, ws_id, now_utc - timedelta(days=2))
        if runs is None:
            logger.warning("Skipping workspace %s this tick — run history unavailable", ws_id)
            continue
        if not is_due(ws, now_utc, runs):
            continue
        try:
            outcomes.append({"workspace_id": ws_id, **run_workspace_digest(ws_id, ws)})
        except Exception:
            logger.exception("Scheduler tick: workspace %s failed", ws_id)
    return outcomes
