"""Per-workspace webhook ingestion: signatures checked against the
workspace's own secret, rows stamped with the workspace, dedup per workspace."""
import hashlib
import hmac
import json

import pytest

PR_OPENED = {
    "action": "opened",
    "pull_request": {
        "number": 42, "title": "Fix rounding", "html_url": "https://github.com/acme/pricing/pull/42",
        "user": {"login": "dev-builds"}, "merged": False,
        "base": {"ref": "main"}, "head": {"ref": "fix"}, "draft": False,
    },
    "repository": {"full_name": "acme/pricing"},
}


def _workspace(db, secret: str | None = "s3cret-value") -> str:
    ws = db.table("workspaces").insert({"name": "Acme"}).execute().data[0]
    if secret:
        db.table("workspace_integrations").insert({
            "workspace_id": ws["id"], "provider": "github", "credentials": {"webhook_secret": secret},
        }).execute()
    return ws["id"]


def _post(client, ws_id: str, payload: dict, secret: str, event: str = "pull_request"):
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        f"/webhooks/github/{ws_id}",
        content=body,
        headers={"X-GitHub-Event": event, "X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )


def test_signed_delivery_is_stored_under_its_workspace(client, db):
    ws = _workspace(db)
    assert _post(client, ws, PR_OPENED, "s3cret-value").status_code == 204
    rows = db.tables["activity_events"]
    assert len(rows) == 1
    assert rows[0]["workspace_id"] == ws
    assert rows[0]["actor"] == "dev-builds"
    assert rows[0]["dedup_key"] == "github:pr:acme/pricing:42:pr_opened"


def test_redelivery_is_deduplicated(client, db):
    ws = _workspace(db)
    _post(client, ws, PR_OPENED, "s3cret-value")
    _post(client, ws, PR_OPENED, "s3cret-value")
    assert len(db.tables["activity_events"]) == 1


def test_same_event_in_two_workspaces_is_two_rows(client, db):
    a, b = _workspace(db, "secret-a-value"), _workspace(db, "secret-b-value")
    _post(client, a, PR_OPENED, "secret-a-value")
    _post(client, b, PR_OPENED, "secret-b-value")
    assert sorted(r["workspace_id"] for r in db.tables["activity_events"]) == sorted([a, b])


def test_another_workspaces_secret_is_rejected(client, db):
    a, b = _workspace(db, "secret-a-value"), _workspace(db, "secret-b-value")
    assert _post(client, a, PR_OPENED, "secret-b-value").status_code == 401
    assert db.tables.get("activity_events", []) == []


@pytest.mark.parametrize("headers", [{}, {"X-Hub-Signature-256": "sha256=deadbeef"}])
def test_missing_or_bad_signature_is_401(client, db, headers):
    ws = _workspace(db)
    resp = client.post(
        f"/webhooks/github/{ws}", content=json.dumps(PR_OPENED).encode(),
        headers={"X-GitHub-Event": "pull_request", **headers},
    )
    assert resp.status_code == 401


def test_workspace_without_secret_rejects_everything(client, db):
    ws = _workspace(db, secret=None)
    assert _post(client, ws, PR_OPENED, "anything-at-all").status_code == 401


def test_unknown_workspace_is_404(client, db):
    resp = _post(client, "00000000-0000-0000-0000-00000000dead", PR_OPENED, "x")
    assert resp.status_code == 404


def test_identity_aliases_are_per_workspace(client, db):
    a, b = _workspace(db, "secret-a-value"), _workspace(db, "secret-b-value")
    db.table("actor_aliases").insert({
        "workspace_id": a, "canonical_name": "Dev Okoye", "source": "github", "source_actor": "dev-builds",
    }).execute()
    _post(client, a, PR_OPENED, "secret-a-value")
    _post(client, b, PR_OPENED, "secret-b-value")
    by_ws = {r["workspace_id"]: r["actor"] for r in db.tables["activity_events"]}
    assert by_ws == {a: "Dev Okoye", b: "dev-builds"}


def test_figma_passcode_is_per_workspace(client, db):
    ws = db.table("workspaces").insert({"name": "Acme"}).execute().data[0]["id"]
    db.table("workspace_integrations").insert({
        "workspace_id": ws, "provider": "figma", "credentials": {"webhook_secret": "figma-pass"},
    }).execute()
    payload = {"event_type": "PING", "passcode": "wrong"}
    assert client.post(f"/webhooks/figma/{ws}", json=payload).status_code == 401
    assert client.post(f"/webhooks/figma/{ws}", json={**payload, "passcode": "figma-pass"}).status_code == 204
