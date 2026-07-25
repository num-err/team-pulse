import logging
import time
from datetime import datetime, timedelta, timezone

import anthropic
from fastapi import HTTPException, status

from app.config import get_settings
from app.integrations.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Transient: network hiccup, rate limit, or Anthropic-side outage/overload —
# worth one retry, then a 503 (retry later) if it's still failing.
_TRANSIENT_ANTHROPIC_ERRORS = (
    anthropic.APIConnectionError,  # includes APITimeoutError
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.OverloadedError,
)
_RETRY_BACKOFF_SECONDS = 1.5


def _call_claude(client: anthropic.Anthropic, **kwargs):
    """Call Claude with one retry on transient failure.

    Transient (timeout, rate limit, Anthropic-side 5xx/overload) -> retried
    once after a short backoff, then HTTP 503 if still failing.
    Permanent (bad auth, bad request, etc.) -> HTTP 502 immediately, no retry.
    """
    for attempt in (1, 2):
        try:
            return client.messages.create(**kwargs)
        except _TRANSIENT_ANTHROPIC_ERRORS as exc:
            logger.warning(
                "Anthropic call failed (attempt %d/2, transient %s): %s",
                attempt, type(exc).__name__, exc,
            )
            if attempt == 2:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"AI service temporarily unavailable ({type(exc).__name__}) — try again shortly.",
                ) from exc
            time.sleep(_RETRY_BACKOFF_SECONDS)
        except anthropic.APIError as exc:
            logger.error("Anthropic call failed (permanent %s): %s", type(exc).__name__, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error ({type(exc).__name__}): {exc}",
            ) from exc


_SYSTEM_PROMPT = (
    "You are a progress summarization assistant for a software team. "
    "Given the following raw activity data for {actor} on {date}, write a 2-4 sentence "
    "plain-English summary of what they accomplished. Write in third person. Be specific. "
    "Keep it under 100 words. No bullet points."
)

MODEL = "claude-haiku-4-5"


def generate_digest(actor: str) -> dict:
    supabase = get_supabase()

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    result = (
        supabase.table("activity_events")
        .select("*")
        .eq("actor", actor)
        .gte("received_at", since.isoformat())
        .execute()
    )

    events = result.data or []
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No activity found for '{actor}' in the last 24 hours.",
        )

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events_text = "\n".join(
        f"- [{e['event_type']}] {e.get('repo', '')} — {e.get('title', '')} ({e.get('url', '')})"
        for e in events
    )

    client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
    response = _call_claude(
        client,
        model=MODEL,
        max_tokens=256,
        system=_SYSTEM_PROMPT.format(actor=actor, date=date_str),
        messages=[{"role": "user", "content": events_text}],
    )

    return {
        "summary": response.content[0].text.strip(),
        "actor": actor,
        "date": date_str,
        "event_count": len(events),
    }
