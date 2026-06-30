from datetime import datetime, timedelta, timezone

import anthropic
from fastapi import HTTPException, status

from app.config import get_settings
from app.integrations.supabase_client import get_supabase
from app.services.digest import MODEL, generate_digest

_TEAM_SYSTEM_PROMPT = (
    "You are a progress summarization assistant for a software team. "
    "The following are individual standup summaries for each team member on {date}. "
    "Write a 3-5 sentence team standup that captures the group's overall progress. "
    "Be specific, highlight the most impactful work, and note any shared themes. "
    "Write in third person. Keep it under 150 words. No bullet points."
)


def generate_team_digest() -> dict:
    supabase = get_supabase()
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    result = (
        supabase.table("activity_events")
        .select("actor")
        .gte("received_at", since.isoformat())
        .execute()
    )

    actors = sorted({row["actor"] for row in (result.data or [])})
    if not actors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No activity found in the last 24 hours.",
        )

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    actor_digests = []
    for actor in actors:
        try:
            actor_digests.append(generate_digest(actor))
        except HTTPException:
            pass  # race: actor had events at discovery but none in digest window

    if not actor_digests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No activity found in the last 24 hours.",
        )

    summaries_text = "\n\n".join(
        f"{d['actor']}: {d['summary']}" for d in actor_digests
    )

    client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=_TEAM_SYSTEM_PROMPT.format(date=date_str),
        messages=[{"role": "user", "content": summaries_text}],
    )

    return {
        "date": date_str,
        "actor_count": len(actor_digests),
        "event_count": sum(d["event_count"] for d in actor_digests),
        "team_summary": response.content[0].text.strip(),
        "actors": [
            {
                "actor": d["actor"],
                "summary": d["summary"],
                "event_count": d["event_count"],
            }
            for d in actor_digests
        ],
    }
