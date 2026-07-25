"""Tests for app.services.health.classify_actor().

classify_actor() is a pure function (events + a fixed `now` in, a
classification dict out) — no Supabase mocking needed. Every test below
constructs event lists directly and passes an explicit `now`, so results
are deterministic regardless of when the suite actually runs.

Coverage here targets the specific bugs found and fixed across tasks 5 and
5b (THRASHING per-scope forward motion, required struggle signal, source
eligibility) plus the SILENT_STUCK/THRASHING/IDLE priority boundaries —
these are exactly the places already shown to regress silently once
before, per CLAUDE.md's Person Health Engine section.
"""
from datetime import datetime, timedelta, timezone

from app.services.health import THRASHING_MIN_EVENTS, classify_actor

NOW = datetime.now(timezone.utc)


def hours_ago(h: float) -> str:
    return (NOW - timedelta(hours=h)).isoformat()


# ---------------------------------------------------------------------------
# Demo seed regression — the primary regression test named in the task.
# If a future change breaks the exact scenario used in the live pitch
# (PITCH.md), this must fail loudly, not silently drift.
# ---------------------------------------------------------------------------

EXPECTED_STATES = {
    "Sara Kim": "HEALTHY",
    "Priya Sharma": "HEALTHY",
    "Marcus Webb": "HEALTHY",
    "Dev Okoye": "THRASHING",
}

# Pinned exactly as documented in CLAUDE.md's Person Health Engine section
# (updated after the source-eligibility/struggle-signal fix in task 5b,
# which dropped the cross-source "Ticket ... still In Progress" clause).
EXPECTED_DEV_EVIDENCE = (
    "16 commit/edit events to acme/pricing-service over 3 days, 0 merges, 7 CI failures. "
    "One PR open 4d, unmerged."
)


def test_demo_seed_cast_is_exactly_four_people(seed_demo_events_by_actor):
    assert set(seed_demo_events_by_actor.keys()) == set(EXPECTED_STATES.keys())


def test_demo_seed_sara_kim_healthy(seed_demo_module, seed_demo_events_by_actor):
    result = classify_actor("Sara Kim", seed_demo_events_by_actor["Sara Kim"], now=seed_demo_module.now)
    assert result["state"] == "HEALTHY"


def test_demo_seed_priya_sharma_healthy(seed_demo_module, seed_demo_events_by_actor):
    result = classify_actor("Priya Sharma", seed_demo_events_by_actor["Priya Sharma"], now=seed_demo_module.now)
    assert result["state"] == "HEALTHY"


def test_demo_seed_marcus_webb_healthy(seed_demo_module, seed_demo_events_by_actor):
    result = classify_actor("Marcus Webb", seed_demo_events_by_actor["Marcus Webb"], now=seed_demo_module.now)
    assert result["state"] == "HEALTHY"


def test_demo_seed_dev_okoye_thrashing_with_exact_evidence(seed_demo_module, seed_demo_events_by_actor):
    """Dev's evidence string is quoted verbatim in the live pitch narration
    (PITCH.md, per CLAUDE.md) — if the wording or the numbers in it drift,
    the spoken pitch would visibly contradict what's on screen. Pin it
    exactly, not just the state."""
    result = classify_actor("Dev Okoye", seed_demo_events_by_actor["Dev Okoye"], now=seed_demo_module.now)
    assert result["state"] == "THRASHING"
    assert result["evidence"] == EXPECTED_DEV_EVIDENCE


# ---------------------------------------------------------------------------
# Task 5: THRASHING scoped per (source, repo), not actor-wide.
# ---------------------------------------------------------------------------

def test_thrashing_scoped_per_repo_not_masked_by_unrelated_merge():
    """A trivial merge on an unrelated repo must not suppress THRASHING on
    a different repo where the actor is genuinely stalled. Before the
    task-5 fix, this classified HEALTHY (the actor-wide forward-motion bug)."""
    events = []
    for i in range(12):
        events.append({
            "source": "github", "event_type": "commit_pushed", "actor": "casey",
            "repo": "acme/repo-a", "title": f"attempt {i}", "url": f"x{i}",
            "metadata": {"ci_status": "failed"} if i % 3 == 0 else {},
            "received_at": hours_ago(60 - i * 4),
        })
    events.append({
        "source": "github", "event_type": "pr_merged", "actor": "casey",
        "repo": "acme/repo-b", "title": "Bump changelog date", "url": "y",
        "metadata": {}, "received_at": hours_ago(30),
    })

    result = classify_actor("casey", events, now=NOW)

    assert result["state"] == "THRASHING"
    assert "acme/repo-a" in result["evidence"]
    assert "acme/repo-b" not in result["evidence"]


def test_healthy_actor_same_repo_events_and_merge_not_falsely_flagged():
    """Negative control for the scoping fix: high volume AND a real merge
    on the SAME repo must stay HEALTHY, not get caught by an over-corrected
    per-scope check."""
    events = []
    for i in range(9):
        events.append({
            "source": "github", "event_type": "commit_pushed", "actor": "priya-dev",
            "repo": "acme/repo-a", "title": f"incremental change {i}", "url": f"h{i}",
            "metadata": {}, "received_at": hours_ago(50 - i * 4),
        })
    events.append({
        "source": "github", "event_type": "pr_merged", "actor": "priya-dev",
        "repo": "acme/repo-a", "title": "Ship the feature", "url": "p",
        "metadata": {}, "received_at": hours_ago(10),
    })

    result = classify_actor("priya-dev", events, now=NOW)

    assert result["state"] == "HEALTHY"


# ---------------------------------------------------------------------------
# Task 5b: a struggle signal is required, raw volume alone is not enough.
# ---------------------------------------------------------------------------

def test_thrashing_requires_struggle_signal_not_just_volume():
    """8+ commits with no merge over ~3 days is normal mid-feature work --
    must classify HEALTHY without an independent struggle signal (CI
    failure, a stale open PR, or a stuck ticket)."""
    events = [{
        "source": "github", "event_type": "commit_pushed", "actor": "mid-feature-dana",
        "repo": "acme/repo-c", "title": f"incremental work {i}", "url": f"x{i}",
        "metadata": {},  # no ci_status
        "received_at": hours_ago(65 - i * 6),
    } for i in range(THRASHING_MIN_EVENTS + 2)]

    result = classify_actor("mid-feature-dana", events, now=NOW)

    assert result["state"] == "HEALTHY"


def test_thrashing_fires_with_ci_failure_as_the_only_struggle_signal():
    """Positive control for the struggle-signal gate: CI failures alone
    (no PR, no ticket) are sufficient."""
    events = [{
        "source": "github", "event_type": "commit_pushed", "actor": "flaky-fern",
        "repo": "acme/repo-d", "title": f"attempt {i}", "url": f"x{i}",
        "metadata": {"ci_status": "failed"},
        "received_at": hours_ago(65 - i * 6),
    } for i in range(THRASHING_MIN_EVENTS)]

    result = classify_actor("flaky-fern", events, now=NOW)

    assert result["state"] == "THRASHING"


# ---------------------------------------------------------------------------
# Task 5b: source eligibility — Figma/Notion can never trigger THRASHING.
# ---------------------------------------------------------------------------

def test_notion_only_high_volume_is_never_thrashing():
    events = [{
        "source": "notion", "event_type": "page_edited", "actor": "writer-priya",
        "repo": "notion", "title": f"doc pass {i}", "url": "x", "metadata": {},
        "received_at": hours_ago(65 - i * 6),
    } for i in range(10)]

    result = classify_actor("writer-priya", events, now=NOW)

    assert result["state"] != "THRASHING"


def test_figma_only_high_volume_is_never_thrashing():
    events = [{
        "source": "figma", "event_type": "file_comment" if i % 2 == 0 else "version_saved",
        "actor": "designer-sara", "repo": "Checkout Redesign", "title": f"note {i}",
        "url": "x", "metadata": {}, "received_at": hours_ago(65 - i * 6),
    } for i in range(10)]

    result = classify_actor("designer-sara", events, now=NOW)

    assert result["state"] != "THRASHING"


# ---------------------------------------------------------------------------
# Priority ordering: SILENT_STUCK vs THRASHING vs IDLE.
# ---------------------------------------------------------------------------

def test_silent_stuck_takes_priority_when_both_conditions_hold():
    """SILENT_STUCK and THRASHING can both be independently satisfied by
    the same raw events (an open ticket + 48h+ silence, AND 8+ same-repo
    events with zero forward motion and a struggle signal, landed 48-72h
    ago). classify_actor()'s early-return priority order must pick
    SILENT_STUCK -- see the corrected priority-ordering note in CLAUDE.md's
    Person Health Engine section (this is priority-ordering, not the two
    conditions being mutually exclusive)."""
    events = [{
        "source": "linear", "event_type": "issue_started", "actor": "quiet-sam",
        "repo": "ENG", "title": "Investigate slow query", "url": "x",
        "metadata": {"identifier": "ENG-9"}, "received_at": hours_ago(70),
    }]
    for i in range(THRASHING_MIN_EVENTS):
        events.append({
            "source": "github", "event_type": "commit_pushed", "actor": "quiet-sam",
            "repo": "acme/svc", "title": f"attempt {i}", "url": f"x{i}",
            "metadata": {"ci_status": "failed"}, "received_at": hours_ago(69 - i * 2),
        })
    result = classify_actor("quiet-sam", events, now=NOW)

    assert result["state"] == "SILENT_STUCK"


def test_idle_when_no_events_at_all():
    result = classify_actor("ghost", [], now=NOW)
    assert result["state"] == "IDLE"


def test_idle_not_silent_stuck_when_inactive_with_no_open_ticket():
    """Pure inactivity (nothing recent, nothing open) is IDLE -- rendered
    neutrally -- not SILENT_STUCK, which specifically requires an open
    ticket left 'In Progress'."""
    events = [{
        "source": "github", "event_type": "pr_merged", "actor": "on-break",
        "repo": "acme/svc", "title": "Ship feature", "url": "x", "metadata": {},
        "received_at": hours_ago(24 * 10),  # 10 days ago, outside every window
    }]

    result = classify_actor("on-break", events, now=NOW)

    assert result["state"] == "IDLE"


def test_open_ticket_alone_is_not_silent_stuck_if_still_active():
    """An open ticket doesn't trigger SILENT_STUCK if the actor has a
    recent event elsewhere (< 48h) -- silence is required, not just an
    open ticket."""
    events = [
        {"source": "linear", "event_type": "issue_started", "actor": "busy-tia",
         "repo": "ENG", "title": "Refactor auth", "url": "x",
         "metadata": {"identifier": "ENG-5"}, "received_at": hours_ago(60)},
        {"source": "github", "event_type": "commit_pushed", "actor": "busy-tia",
         "repo": "acme/other-repo", "title": "unrelated work", "url": "y",
         "metadata": {}, "received_at": hours_ago(2)},
    ]

    result = classify_actor("busy-tia", events, now=NOW)

    assert result["state"] != "SILENT_STUCK"
