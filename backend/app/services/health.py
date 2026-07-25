"""Per-actor health classification from raw activity_events.

Four states:
  HEALTHY      — events flowing AND forward motion (merge/completion/milestone) in the last 72h
  THRASHING    — 8+ activity events in 72h concentrated on one work context
                 (same source + repo), zero forward motion in that context —
                 scoped per-context so progress elsewhere doesn't mask it
  SILENT_STUCK — a Linear ticket left "In Progress" and zero activity of any kind for 48h+
  IDLE         — no events, no open in-progress work (neutral, not a problem)
"""

from datetime import datetime, timedelta, timezone

from app.integrations.supabase_client import get_supabase

LOOKBACK_DAYS = 14
ACTIVITY_WINDOW_HOURS = 72
STUCK_THRESHOLD_HOURS = 48
THRASHING_MIN_EVENTS = 8
# A PR younger than this isn't evidence of struggle yet, just normal in-flight
# work — only a PR that's sat open a while counts as a struggle signal.
STRUGGLE_PR_MIN_AGE_HOURS = 24

COMPLETION_EVENT_TYPES = {"pr_merged", "issue_completed"}
_TICKET_LIFECYCLE_TYPES = {"issue_created", "issue_started", "issue_completed", "issue_cancelled"}
_PR_LIFECYCLE_TYPES = {"pr_opened", "pr_merged", "pr_closed"}
# Only sources with a defined completion event type can prove "zero forward
# motion" means anything. Figma (file_comment/version_saved) and Notion
# (page_created/page_edited) have no such event — a busy documentation week
# or an active design-review thread would otherwise be structurally
# indistinguishable from someone stuck. See CLAUDE.md Person Health Engine.
_THRASHING_ELIGIBLE_SOURCES = {"github", "linear"}

_EVIDENCE_LABELS = {
    "pr_merged": "a PR merged",
    "issue_completed": "a ticket moved to Done",
}


def _hours_since(received_at: str, now: datetime) -> float:
    ts = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
    return (now - ts).total_seconds() / 3600


def _ticket_key(row: dict) -> str:
    metadata = row.get("metadata") or {}
    return (
        metadata.get("identifier")
        or metadata.get("issue_identifier")
        or f"{row.get('repo')}::{row.get('title')}"
    )


def _open_tickets(events: list[dict]) -> list[dict]:
    """Linear tickets whose latest lifecycle event is issue_started — still 'In Progress'."""
    latest_by_ticket: dict[str, dict] = {}
    for row in events:
        if row["source"] != "linear" or row["event_type"] not in _TICKET_LIFECYCLE_TYPES:
            continue
        latest_by_ticket[_ticket_key(row)] = row  # events are pre-sorted ascending
    return [row for row in latest_by_ticket.values() if row["event_type"] == "issue_started"]


def _open_prs(events: list[dict], repo: str) -> list[dict]:
    """GitHub PRs on `repo` whose latest lifecycle event is pr_opened — still unmerged."""
    latest_by_pr: dict[str, dict] = {}
    for row in events:
        if row["source"] != "github" or row.get("repo") != repo or row["event_type"] not in _PR_LIFECYCLE_TYPES:
            continue
        metadata = row.get("metadata") or {}
        key = metadata.get("pr_number") or row.get("url") or row.get("title")
        latest_by_pr[key] = row
    return [row for row in latest_by_pr.values() if row["event_type"] == "pr_opened"]


def _is_forward_motion(row: dict) -> bool:
    if row["event_type"] in COMPLETION_EVENT_TYPES:
        return True
    return bool((row.get("metadata") or {}).get("milestone"))


def _scope_key(row: dict) -> tuple[str, str]:
    """Group an event into a 'work context' for THRASHING concentration.

    Scoped to (source, repo), not repo alone. `repo` already means a
    different kind of thing per source — an actual git repo for GitHub, a
    team key for Linear, a file name for Figma, and always the literal
    string "notion" for Notion — so there is no consistent identity across
    sources to group on; this deliberately does not invent one, and scopes
    within source instead.

    An event with no repo value gets its own singleton scope (keyed on the
    row's own id) rather than collapsing into one shared "unknown" bucket
    with every other repo-less event — those are likely unrelated pieces of
    work, and treating them as "concentrated on one thing" would itself be
    a false signal.
    """
    source = row.get("source") or "unknown"
    repo = row.get("repo")
    if repo:
        return (source, repo)
    return (source, f"__no_repo__:{row.get('id') or id(row)}")


def classify_actor(actor: str, events: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)

    if not events:
        return {
            "actor": actor,
            "state": "IDLE",
            "evidence": "No recorded activity.",
        }

    events = sorted(events, key=lambda e: e["received_at"])
    hours_since_last = _hours_since(events[-1]["received_at"], now)
    open_tickets = _open_tickets(events)
    events_72h = [e for e in events if _hours_since(e["received_at"], now) <= ACTIVITY_WINDOW_HOURS]
    forward_motion_72h = [e for e in events_72h if _is_forward_motion(e)]

    # SILENT_STUCK: something left "In Progress", and this person has gone dark entirely.
    if open_tickets and hours_since_last >= STUCK_THRESHOLD_HOURS:
        ticket = open_tickets[0]
        evidence = (
            f"\"{ticket.get('title')}\" marked In Progress, "
            f"no activity of any kind for {round(hours_since_last)}h."
        )
        return {"actor": actor, "state": "SILENT_STUCK", "evidence": evidence}

    # THRASHING: high volume + zero forward motion + an independent struggle
    # signal (CI failure / a PR that's sat open / a ticket still In Progress)
    # — all within the SAME (source, repo) work context via _scope_key.
    # Deliberately tuned for precision over recall: a false THRASHING
    # publicly mislabels someone as struggling in the team channel, which is
    # far more costly than missing a real case, so raw event count alone
    # must never be sufficient — 8+ commits with no merge in 3 days is
    # normal mid-feature work, not evidence of anything by itself. Also why
    # eligibility is restricted to sources with a defined completion event
    # (see _THRASHING_ELIGIBLE_SOURCES) — without one, "zero forward motion"
    # can't be distinguished from "this source doesn't have that concept."
    groups: dict[tuple[str, str], list[dict]] = {}
    for e in events_72h:
        if e.get("source") not in _THRASHING_ELIGIBLE_SOURCES:
            continue
        groups.setdefault(_scope_key(e), []).append(e)

    stalled_groups = [
        (key, group_events)
        for key, group_events in groups.items()
        if not any(_is_forward_motion(e) for e in group_events)
    ]
    if stalled_groups:
        (_, repo), group_events = max(stalled_groups, key=lambda kv: len(kv[1]))
        failures = sum(
            1 for e in group_events if (e.get("metadata") or {}).get("ci_status") == "failed"
        )
        stale_open_prs = [
            pr for pr in _open_prs(events, repo)
            if _hours_since(pr["received_at"], now) >= STRUGGLE_PR_MIN_AGE_HOURS
        ]
        group_open_tickets = [t for t in open_tickets if t.get("repo") == repo]
        has_struggle_signal = bool(failures or stale_open_prs or group_open_tickets)

        if len(group_events) >= THRASHING_MIN_EVENTS and has_struggle_signal:
            oldest = min(e["received_at"] for e in group_events)
            span_days = max(1, round(_hours_since(oldest, now) / 24))

            note = ""
            if stale_open_prs:
                days_open = round(_hours_since(stale_open_prs[0]["received_at"], now) / 24)
                note += f" One PR open {days_open}d, unmerged."
            if group_open_tickets:
                note += f" Ticket \"{group_open_tickets[0].get('title')}\" still In Progress."

            evidence = (
                f"{len(group_events)} commit/edit events to {repo} over {span_days} "
                f"day{'s' if span_days != 1 else ''}, 0 merges"
                f"{f', {failures} CI failures' if failures else ''}.{note}"
            )
            return {"actor": actor, "state": "THRASHING", "evidence": evidence}

    # HEALTHY: things are moving and something landed.
    if forward_motion_72h:
        comp_desc = ", ".join(sorted({_EVIDENCE_LABELS.get(e["event_type"], "a milestone") for e in forward_motion_72h}))
        evidence = f"{len(events_72h)} events in the last 3 days, including {comp_desc}."
        return {"actor": actor, "state": "HEALTHY", "evidence": evidence}

    if events_72h:
        evidence = f"{len(events_72h)} events in the last 3 days."
        return {"actor": actor, "state": "HEALTHY", "evidence": evidence}

    return {
        "actor": actor,
        "state": "IDLE",
        "evidence": "No open in-progress work and no activity in the last 3 days.",
    }


def get_actor_health(actor: str) -> dict:
    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=LOOKBACK_DAYS)

    result = (
        supabase.table("activity_events")
        .select("*")
        .eq("actor", actor)
        .gte("received_at", since.isoformat())
        .order("received_at")
        .execute()
    )

    return classify_actor(actor, result.data or [], now)


_STATE_PRIORITY = {"SILENT_STUCK": 0, "THRASHING": 1, "HEALTHY": 2, "IDLE": 3}


def classify_team_health() -> list[dict]:
    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=LOOKBACK_DAYS)

    result = (
        supabase.table("activity_events")
        .select("*")
        .gte("received_at", since.isoformat())
        .order("received_at")
        .execute()
    )

    by_actor: dict[str, list[dict]] = {}
    for row in result.data or []:
        by_actor.setdefault(row["actor"], []).append(row)

    results = [classify_actor(actor, events, now) for actor, events in by_actor.items()]
    results.sort(key=lambda r: (_STATE_PRIORITY[r["state"]], r["actor"]))
    return results
