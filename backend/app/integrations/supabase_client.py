from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    """Return a cached Supabase client.

    Reads SUPABASE_URL and SUPABASE_KEY from settings. Raises if either is
    missing so misconfiguration fails fast at first use.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set (see backend/.env.example)."
        )
    return create_client(settings.supabase_url, settings.supabase_key)
