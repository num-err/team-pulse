from datetime import datetime, timedelta, timezone

import anthropic
from fastapi import APIRouter, HTTPException, Query, status

from app.config import get_settings
from app.integrations.supabase_client import get_supabase

router = APIRouter(prefix="/digest", tags=["digest"])

_SYSTEM_PROMPT = (
    "You are a progress summarization assistant for a software team. "
    "Given the following raw activity data for {actor} on {date}, write a 2-4 sentence "
    "plain-English summary of what they accomplished. Write in third person. Be specific. "
    "Keep it under 100 words. No bullet points."
)

MODEL = "claude-haiku-4-5"


@router.post("/generate")
def generate_digest(actor: str = Query(..., description="GitHub username to summarize")):
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
    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=_SYSTEM_PROMPT.format(actor=actor, date=date_str),
        messages=[{"role": "user", "content": events_text}],
    )

    summary = response.content[0].text.strip()

    return {
        "summary": summary,
        "actor": actor,
        "date": date_str,
        "event_count": len(events),
    }
