"""Tests for app.services.blockers.find_blockers().

Unlike classify_actor(), find_blockers() is not pure — it calls
get_supabase() directly and reads datetime.now() internally rather than
accepting it as a parameter. Tested here against a fake Supabase client
(monkeypatched onto app.services.blockers.get_supabase) instead of a real
one, so the suite needs no network or live project.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import app.services.blockers as blockers_mod
from app.services.blockers import BLOCKER_THRESHOLD_HOURS, find_blockers

NOW = datetime.now(timezone.utc)


def hours_ago(h: float) -> str:
    return (NOW - timedelta(hours=h)).isoformat()


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, field, value):
        self._rows = [r for r in self._rows if r.get(field) == value]
        return self

    def gte(self, field, value):
        self._rows = [r for r in self._rows if r.get(field, "") >= value]
        return self

    def order(self, field, desc=False):
        self._rows = sorted(self._rows, key=lambda r: r[field], reverse=desc)
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _FakeSupabase:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        assert name == "activity_events"
        return _FakeQuery(list(self._rows))


def _patch_supabase(monkeypatch, rows: list[dict]) -> None:
    monkeypatch.setattr(blockers_mod, "get_supabase", lambda: _FakeSupabase(rows))


def test_stale_in_progress_issue_is_flagged_with_correct_hours(monkeypatch):
    rows = [{
        "source": "linear", "event_type": "issue_started", "actor": "Ada Chen",
        "repo": "DESIGN", "title": "Payment UI Review", "url": "https://linear.app/x",
        "metadata": {"identifier": "DESIGN-1"}, "received_at": hours_ago(52),
    }]
    _patch_supabase(monkeypatch, rows)

    blockers = find_blockers()

    assert len(blockers) == 1
    assert blockers[0]["title"] == "Payment UI Review"
    assert blockers[0]["actor"] == "Ada Chen"
    assert blockers[0]["hours_since_activity"] == 52


def test_fresh_in_progress_issue_is_not_flagged(monkeypatch):
    rows = [{
        "source": "linear", "event_type": "issue_started", "actor": "Marcus Webb",
        "repo": "ENG", "title": "Fresh ticket", "url": "x",
        "metadata": {"identifier": "ENG-99"}, "received_at": hours_ago(3),
    }]
    _patch_supabase(monkeypatch, rows)

    assert find_blockers() == []


def test_completed_ticket_is_not_flagged_even_though_it_was_started_long_ago(monkeypatch):
    """Only the LATEST lifecycle event per issue matters -- a ticket that
    was started 80h ago but has since moved to Done isn't a blocker."""
    rows = [
        {"source": "linear", "event_type": "issue_started", "actor": "Priya Sharma",
         "repo": "PM", "title": "Old but resolved", "url": "x",
         "metadata": {"identifier": "PM-1"}, "received_at": hours_ago(80)},
        {"source": "linear", "event_type": "issue_completed", "actor": "Priya Sharma",
         "repo": "PM", "title": "Old but resolved", "url": "x",
         "metadata": {"identifier": "PM-1"}, "received_at": hours_ago(10)},
    ]
    _patch_supabase(monkeypatch, rows)

    assert find_blockers() == []


def test_threshold_boundary_is_flagged(monkeypatch):
    """At exactly BLOCKER_THRESHOLD_HOURS, the issue counts as stale (the
    check is `>=`, not `>`)."""
    rows = [{
        "source": "linear", "event_type": "issue_started", "actor": "Dev Okoye",
        "repo": "ENG", "title": "Boundary ticket", "url": "x",
        "metadata": {"identifier": "ENG-1"},
        "received_at": (NOW - timedelta(hours=BLOCKER_THRESHOLD_HOURS)).isoformat(),
    }]
    _patch_supabase(monkeypatch, rows)

    assert len(find_blockers()) == 1


def test_non_linear_events_are_ignored(monkeypatch):
    """A stale-looking GitHub or Figma event must never be treated as a
    blocker -- only source == 'linear' is in scope."""
    rows = [{
        "source": "github", "event_type": "pr_opened", "actor": "num-err",
        "repo": "acme/repo", "title": "Old open PR", "url": "x",
        "metadata": {}, "received_at": hours_ago(100),
    }]
    _patch_supabase(monkeypatch, rows)

    assert find_blockers() == []
