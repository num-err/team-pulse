from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings

# Tests install an in-memory fake here (see tests/fakes.py) so every module's
# get_supabase() call hits the fake, regardless of how it imported the name.
_override = None


def set_supabase_override(client) -> None:
    """Testing hook: make get_supabase() return `client` (None to clear)."""
    global _override
    _override = client


def get_supabase() -> Client:
    """Return the Supabase client (service-role).

    Raises if SUPABASE_URL / SUPABASE_KEY are missing so misconfiguration
    fails fast at first use.
    """
    if _override is not None:
        return _override
    return _real_client()


@lru_cache
def _real_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set (see backend/.env.example)."
        )
    return create_client(settings.supabase_url, settings.supabase_key)
