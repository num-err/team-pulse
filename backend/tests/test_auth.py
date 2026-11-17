"""Access-token verification: only valid, unexpired, correctly-scoped
Supabase tokens get through."""
import base64
import json
import time

from tests.conftest import auth


def test_valid_token_reaches_me(client, token_for):
    resp = client.get("/me", headers=auth(token_for(user_id="11111111-1111-1111-1111-111111111111", email="a@x.com")))
    assert resp.status_code == 200
    assert resp.json() == {
        "user": {"id": "11111111-1111-1111-1111-111111111111", "email": "a@x.com"},
        "workspaces": [],
    }


def test_missing_token_is_401(client):
    assert client.get("/me").status_code == 401


def test_garbage_token_is_401(client):
    assert client.get("/me", headers=auth("not-a-jwt")).status_code == 401


def test_expired_token_is_401(client, token_for):
    past = int(time.time()) - 60
    resp = client.get("/me", headers=auth(token_for(exp=past, iat=past - 3600)))
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Access token expired"


def test_wrong_audience_is_401(client, token_for):
    assert client.get("/me", headers=auth(token_for(aud="anon"))).status_code == 401


def test_other_projects_issuer_is_401(client, token_for):
    token = token_for(iss="https://some-other-project.supabase.co/auth/v1")
    assert client.get("/me", headers=auth(token)).status_code == 401


def test_wrong_signing_secret_is_401(client, token_for):
    token = token_for(_secret="an-attacker-chosen-secret-of-sufficient-length")
    assert client.get("/me", headers=auth(token)).status_code == 401


def test_unsigned_alg_none_token_is_401(client):
    def b64(obj) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    claims = {
        "sub": "x", "aud": "authenticated", "iss": "https://test-project.supabase.co/auth/v1",
        "exp": int(time.time()) + 3600,
    }
    token = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64(claims)}."
    assert client.get("/me", headers=auth(token)).status_code == 401


def test_data_routes_require_auth(client):
    ws = "00000000-0000-0000-0000-000000000001"
    for method, path in [
        ("post", f"/workspaces/{ws}/digest/team"),
        ("get", f"/workspaces/{ws}/health/team"),
        ("get", f"/workspaces/{ws}/integrations"),
        ("post", f"/workspaces/{ws}/scheduler/run-now"),
    ]:
        assert getattr(client, method)(path).status_code == 401, path
