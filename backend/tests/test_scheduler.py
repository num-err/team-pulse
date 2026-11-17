"""Per-workspace scheduling: due in the team's own timezone, at most one
delivered digest per local day, bounded retries, fail-closed."""
from datetime import datetime, timezone

import pytest

import app.services.scheduler as sched
from app.services.scheduler import MAX_ATTEMPTS_PER_DAY, is_due

NY = {"id": "ws-ny", "timezone": "America/New_York", "digest_hour": 9, "digest_minute": 0}


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


# Nov 16 2026: New York is UTC-5, so 9:00 local == 14:00 UTC.

def test_not_due_before_local_digest_time():
    assert is_due(NY, utc(2026, 11, 16, 13, 59), []) is False


def test_due_after_local_digest_time():
    assert is_due(NY, utc(2026, 11, 16, 14, 0), []) is True


def test_utc_morning_is_still_previous_local_day():
    # 03:00 UTC on the 17th is 22:00 on the 16th in New York — a run at
    # 14:05 UTC on the 16th already covers that local day.
    runs = [{"ran_at": "2026-11-16T14:05:00+00:00", "status": "delivered"}]
    assert is_due(NY, utc(2026, 11, 17, 3, 0), runs) is False


def test_not_due_again_after_delivery_today():
    runs = [{"ran_at": "2026-11-16T14:01:00+00:00", "status": "delivered"}]
    assert is_due(NY, utc(2026, 11, 16, 18, 0), runs) is False


def test_yesterdays_delivery_does_not_block_today():
    runs = [{"ran_at": "2026-11-15T14:01:00+00:00", "status": "delivered"}]
    assert is_due(NY, utc(2026, 11, 16, 14, 15), runs) is True


@pytest.mark.parametrize("status", ["no_activity", "not_configured"])
def test_quiet_or_unconfigured_days_are_settled(status):
    runs = [{"ran_at": "2026-11-16T14:01:00+00:00", "status": status}]
    assert is_due(NY, utc(2026, 11, 16, 15, 0), runs) is False


def test_errors_are_retried_up_to_the_daily_cap():
    error = {"ran_at": "2026-11-16T14:01:00+00:00", "status": "error"}
    assert is_due(NY, utc(2026, 11, 16, 15, 0), [error] * (MAX_ATTEMPTS_PER_DAY - 1)) is True
    assert is_due(NY, utc(2026, 11, 16, 15, 0), [error] * MAX_ATTEMPTS_PER_DAY) is False


def test_unknown_timezone_falls_back_to_utc():
    ws = {**NY, "timezone": "Not/AZone"}
    assert is_due(ws, utc(2026, 11, 16, 8, 59), []) is False
    assert is_due(ws, utc(2026, 11, 16, 9, 0), []) is True


# ------------------------------------------------------------ tick behaviour


@pytest.fixture
def posted(db, monkeypatch):
    """Two workspaces; generation and Slack posting faked out."""
    calls: list[str] = []
    monkeypatch.setattr(sched, "generate_team_digest", lambda ws_id: {"actor_count": 1, "event_count": 3, "ws": ws_id})
    monkeypatch.setattr(sched, "post_team_digest", lambda digest, dest: calls.append(digest["ws"]) or "1700000000.1")
    monkeypatch.setattr(sched, "notion_token_for", lambda ws_id: None)
    sched._delivered_memo.clear()
    for name in ("Acme", "Globex"):
        ws = db.table("workspaces").insert({"name": name, "timezone": "America/New_York"}).execute().data[0]
        db.table("workspace_integrations").insert({
            "workspace_id": ws["id"], "provider": "slack",
            "credentials": {"bot_token": "xoxb-t"}, "settings": {"channel": "C0123ABCD"},
        }).execute()
    return calls


def test_tick_delivers_each_due_workspace_exactly_once(db, posted):
    now = utc(2026, 11, 16, 14, 5)
    sched.run_due_workspaces(now)
    sched._delivered_memo.clear()  # prove job_runs alone prevents a repeat
    sched.run_due_workspaces(utc(2026, 11, 16, 14, 20))
    assert len(posted) == 2
    assert len(set(posted)) == 2


def test_tick_skips_when_run_history_is_unreadable(db, posted):
    db.fail_tables.add("job_runs")
    sched.run_due_workspaces(utc(2026, 11, 16, 14, 5))
    assert posted == []


def test_memo_prevents_repeat_if_recording_the_run_failed(db, posted, monkeypatch):
    monkeypatch.setattr(sched, "record_run", lambda *a, **k: False)
    sched.run_due_workspaces(utc(2026, 11, 16, 14, 5))
    sched.run_due_workspaces(utc(2026, 11, 16, 14, 20))
    assert len(posted) == 2


def test_workspace_without_slack_is_settled_not_retried(db, posted):
    db.tables["workspace_integrations"] = db.tables["workspace_integrations"][:1]
    sched.run_due_workspaces(utc(2026, 11, 16, 14, 5))
    sched.run_due_workspaces(utc(2026, 11, 16, 14, 20))
    statuses = sorted(r["result"]["status"] for r in db.tables["job_runs"])
    assert statuses == ["delivered", "not_configured"]
    assert len(posted) == 1
