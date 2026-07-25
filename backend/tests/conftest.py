"""Shared fixtures. No network, no live Supabase — health classification is
tested against pure functions with hand-built event lists; blocker
detection is tested against a fake Supabase client (see test_blockers.py).
"""
import importlib.util
from pathlib import Path

import pytest

_BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def seed_demo_module():
    """Load backend/scripts/seed_demo.py as a module without running its
    main() (which would try to hit a real Supabase project) — importing it
    only executes the top-level EVENTS list construction, guarded by the
    script's own `if __name__ == "__main__":` around main()."""
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
