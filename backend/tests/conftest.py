"""Shared fixtures. No network, no live Supabase, no .env:

- `db` installs an in-memory FakeSupabase behind get_supabase() and points
  settings at a fake project with a known HS256 JWT secret.
- `token_for` mints Supabase-shaped access tokens signed with that secret.
- `client` is a FastAPI TestClient (lifespan not started, so the scheduler
  never runs during tests).
"""
import importlib.util
import time
import uuid
from pathlib import Path

import jwt
import pytest

_BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_SUPABASE_URL = "https://test-project.supabase.co"
TEST_JWT_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"


@pytest.fixture(scope="session")
def seed_demo_module():
    """Load backend/scripts/seed_demo.py as a module without running its
    main() (which would try to hit a real Supabase project)."""
    spec = importlib.util.spec_from_file_location("seed_demo", _BACKEND_DIR / "scripts" / "seed_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def seed_demo_events_by_actor(seed_demo_module):
    by_actor: dict[str, list[dict]] = {}
    for row in seed_demo_module.EVENTS:
        by_actor.setdefault(row["actor"], []).append(row)
    return by_actor


@pytest.fixture
def db(monkeypatch, tmp_path):
    from app.config import get_settings
    from app.integrations.supabase_client import set_supabase_override
    from app.services import identity

    from tests.fakes import FakeSupabase

    monkeypatch.chdir(tmp_path)  # never read backend/.env
    for key, value in {
        "SUPABASE_URL": TEST_SUPABASE_URL,
        "SUPABASE_KEY": "service-role-test",
        "SUPABASE_JWT_SECRET": TEST_JWT_SECRET,
        "APP_ENV": "development",
        "PUBLIC_API_URL": "https://api.test",
        "SLACK_BOT_TOKEN": "",
        "SLACK_DEFAULT_CHANNEL": "",
        "NOTION_TOKEN": "",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    identity.invalidate_cache()

    fake = FakeSupabase()
    set_supabase_override(fake)
    yield fake
    set_supabase_override(None)
    get_settings.cache_clear()
    identity.invalidate_cache()


@pytest.fixture
def token_for():
    def make(user_id: str | None = None, email: str = "user@example.com", **overrides) -> str:
        now = int(time.time())
        claims = {
            "sub": user_id or str(uuid.uuid4()),
            "email": email,
            "aud": "authenticated",
            "iss": f"{TEST_SUPABASE_URL}/auth/v1",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
            **overrides,
        }
        secret = claims.pop("_secret", TEST_JWT_SECRET)
        return jwt.encode(claims, secret, algorithm="HS256")

    return make


@pytest.fixture
def client(db):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
