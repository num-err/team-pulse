"""Cross-source actor identity resolution.

One human can show up under a different handle per source — a GitHub login,
a Linear displayName, a Figma handle, a Notion display name. resolve_actor()
maps a (source, raw handle) pair to a canonical person name via the
`actor_aliases` table, so activity from the same person lands under one
name in activity_events regardless of which tool produced it.

Safety property (the one that matters most): a lookup failure, an unmapped
actor, or the alias table not existing yet must never drop or block an
event. Every failure mode in this file degrades to "pass the raw actor
string through unchanged" — worse for grouping (two entries for one
person) but never worse than that (an event silently vanishing).
"""
import logging
import time
from threading import Lock

from app.integrations.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Short TTL, not a long-lived cache: alias edits (adding/fixing a mapping)
# should take effect for new events within a minute, without hitting
# Supabase on every single webhook delivery in the meantime.
_CACHE_TTL_SECONDS = 60

_cache: dict[tuple[str, str], str] = {}
_cache_loaded_at: float = 0.0
_cache_lock = Lock()


def _normalize(value: str) -> str:
    """Trim + case-fold so "Dev Okoye" and "dev okoye" match the same alias."""
    return value.strip().casefold()


def _load_aliases() -> dict[tuple[str, str], str]:
    supabase = get_supabase()
    result = supabase.table("actor_aliases").select("canonical_name, source, source_actor").execute()
    mapping: dict[tuple[str, str], str] = {}
    for row in result.data or []:
        key = (row["source"], _normalize(row["source_actor"]))
        mapping[key] = row["canonical_name"]
    return mapping


def _get_cache() -> dict[tuple[str, str], str]:
    global _cache, _cache_loaded_at

    now = time.monotonic()
    with _cache_lock:
        is_stale = (now - _cache_loaded_at) > _CACHE_TTL_SECONDS
    if not is_stale:
        return _cache

    try:
        fresh = _load_aliases()
    except Exception:
        # Table missing (migration not run yet), Supabase unreachable, etc.
        # Fall back to the last-known-good cache (empty on the very first
        # failure) rather than raising — identity resolution must never be
        # able to block event ingestion.
        logger.exception("Failed to refresh actor_aliases cache — falling back to raw actor names")
        with _cache_lock:
            _cache_loaded_at = now  # don't retry Supabase on every single call while it's down
        return _cache

    with _cache_lock:
        _cache = fresh
        _cache_loaded_at = now
    return _cache


def resolve_actor(source: str, raw_actor: str) -> str:
    """Map a raw per-source actor string to its canonical name.

    Returns `raw_actor` unchanged if there's no mapping for it, or if alias
    resolution itself fails for any reason — see module docstring.
    """
    if not raw_actor:
        return raw_actor
    cache = _get_cache()
    return cache.get((source, _normalize(raw_actor)), raw_actor)


def invalidate_cache() -> None:
    """Force the next resolve_actor() call to reload from Supabase."""
    global _cache_loaded_at
    with _cache_lock:
        _cache_loaded_at = 0.0
