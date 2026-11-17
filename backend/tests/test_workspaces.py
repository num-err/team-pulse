"""Workspace creation, membership enforcement, roles, integration secrets,
and — most important — that one team can never read another team's data."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from tests.conftest import auth

ALICE = "aaaaaaaa-0000-0000-0000-000000000001"
BOB = "bbbbbbbb-0000-0000-0000-000000000002"


@pytest.fixture
def alice(token_for):
    return auth(token_for(user_id=ALICE, email="alice@acme.com"))


@pytest.fixture
def bob(token_for):
    return auth(token_for(user_id=BOB, email="bob@globex.com"))


def _create(client, headers, name="Acme", tz="America/New_York") -> dict:
    resp = client.post("/workspaces", json={"name": name, "timezone": tz}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_creator_becomes_owner_and_sees_workspace(client, alice):
    ws = _create(client, alice)
    assert ws["role"] == "owner"
    assert ws["timezone"] == "America/New_York"
    me = client.get("/me", headers=alice).json()
    assert [w["id"] for w in me["workspaces"]] == [ws["id"]]


def test_invalid_timezone_is_rejected(client, alice):
    resp = client.post("/workspaces", json={"name": "Acme", "timezone": "Mars/Olympus"}, headers=alice)
    assert resp.status_code == 422


def test_non_member_gets_404_not_403(client, alice, bob):
    ws = _create(client, alice)
    assert client.get(f"/workspaces/{ws['id']}", headers=bob).status_code == 404
    assert client.get(f"/workspaces/{ws['id']}", headers=alice).status_code == 200


def test_plain_member_cannot_change_settings_or_integrations(client, db, alice, bob):
    ws = _create(client, alice)
    db.table("workspace_members").insert({"workspace_id": ws["id"], "user_id": BOB, "role": "member"}).execute()

    assert client.get(f"/workspaces/{ws['id']}", headers=bob).status_code == 200
    assert client.patch(f"/workspaces/{ws['id']}", json={"digest_hour": 8}, headers=bob).status_code == 403
    assert client.post(f"/workspaces/{ws['id']}/integrations/github/webhook", headers=bob).status_code == 403
    assert client.post(f"/workspaces/{ws['id']}/scheduler/run-now", headers=bob).status_code == 403


def test_owner_updates_schedule(client, alice):
    ws = _create(client, alice)
    resp = client.patch(f"/workspaces/{ws['id']}", json={"digest_hour": 8, "digest_minute": 30}, headers=alice)
    assert resp.status_code == 200
    assert (resp.json()["digest_hour"], resp.json()["digest_minute"]) == (8, 30)
    bad = client.patch(f"/workspaces/{ws['id']}", json={"digest_hour": 24}, headers=alice)
    assert bad.status_code == 422


def test_webhook_secret_is_shown_once_and_never_listed(client, alice):
    ws = _create(client, alice)
    setup = client.post(f"/workspaces/{ws['id']}/integrations/github/webhook", headers=alice).json()
    assert setup["webhook_url"] == f"https://api.test/webhooks/github/{ws['id']}"
    assert len(setup["secret"]) >= 32

    listing = client.get(f"/workspaces/{ws['id']}/integrations", headers=alice)
    assert setup["secret"] not in listing.text
    github = next(i for i in listing.json()["integrations"] if i["provider"] == "github")
    assert github["connected"] is True


def test_slack_setup_validates_token_and_never_returns_it(client, alice, monkeypatch):
    import app.routes.workspaces as routes

    class _FakeWebClient:
        def __init__(self, token):
            self.token = token

        def auth_test(self):
            return {"team": "Acme", "team_id": "T123"}

    monkeypatch.setattr(routes, "WebClient", _FakeWebClient)
    ws = _create(client, alice)
    resp = client.put(
        f"/workspaces/{ws['id']}/integrations/slack",
        json={"bot_token": "xoxb-secret-token", "channel": "C0123ABCD"},
        headers=alice,
    )
    assert resp.status_code == 200, resp.text
    assert "xoxb-secret-token" not in resp.text
    assert "xoxb-secret-token" not in client.get(f"/workspaces/{ws['id']}/integrations", headers=alice).text

    # A channel *name* instead of an ID is rejected up front.
    bad = client.put(
        f"/workspaces/{ws['id']}/integrations/slack",
        json={"bot_token": "xoxb-x", "channel": "#standup"},
        headers=alice,
    )
    assert bad.status_code == 422


def test_team_digest_only_sees_own_workspace(client, db, alice, bob, monkeypatch):
    """The core multi-tenancy guarantee: Alice's digest never includes
    Globex's people or events, and Bob can't request Acme's digest at all."""
    import app.services.digest as digest_mod
    import app.services.team_digest as team_mod

    def fake_claude(_client, **kwargs):
        # Echo the full prompt input, so any leaked event text shows up in the response.
        return SimpleNamespace(content=[SimpleNamespace(text=f"summary of: {kwargs['messages'][0]['content']}")])

    monkeypatch.setattr(digest_mod, "_call_claude", fake_claude)
    monkeypatch.setattr(team_mod, "_call_claude", fake_claude)

    acme = _create(client, alice, "Acme")
    globex = _create(client, bob, "Globex")
    recent = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    for ws_id, actor, title in [
        (acme["id"], "Marcus Webb", "Acme checkout fix"),
        (globex["id"], "Hank Scorpio", "Globex secret project"),
        # Same display name on both teams — must not merge across workspaces.
        (globex["id"], "Marcus Webb", "Globex merger docs"),
    ]:
        db.table("activity_events").insert({
            "workspace_id": ws_id, "source": "github", "event_type": "pr_merged",
            "actor": actor, "repo": "x/y", "title": title, "received_at": recent,
        }).execute()

    resp = client.post(f"/workspaces/{acme['id']}/digest/team", headers=alice)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [a["actor"] for a in body["actors"]] == ["Marcus Webb"]
    assert body["event_count"] == 1
    assert body["actors"][0]["health"]["evidence"].startswith("1 events in the last 3 days")
    assert "Globex" not in resp.text and "Hank" not in resp.text

    # Same guarantee for the health engine's team view.
    health = client.get(f"/workspaces/{acme['id']}/health/team", headers=alice).json()
    assert [a["actor"] for a in health["actors"]] == ["Marcus Webb"]
    assert "2 events" not in str(health)

    assert client.post(f"/workspaces/{acme['id']}/digest/team", headers=bob).status_code == 404
    assert client.get(f"/workspaces/{acme['id']}/health/team", headers=bob).status_code == 404
