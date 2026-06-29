import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.integrations.supabase_client import get_supabase
from app.models.activity_event import ActivityEvent

logger = logging.getLogger(__name__)

_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"

_last_sync: dict | None = None
_last_sync_at: datetime | None = None


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _page_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            text = "".join(p.get("text", {}).get("content", "") for p in parts)
            if text:
                return text
    return "Untitled"


def _resolve_user(client: httpx.Client, token: str, user_id: str, cache: dict) -> str:
    if user_id in cache:
        return cache[user_id]
    try:
        resp = client.get(f"{_NOTION_API}/users/{user_id}", headers=_headers(token), timeout=10)
        if resp.is_success:
            name = resp.json().get("name") or user_id
            cache[user_id] = name
            return name
    except Exception:
        pass
    cache[user_id] = user_id
    return user_id


def sync_notion() -> dict:
    global _last_sync, _last_sync_at

    settings = get_settings()
    token = settings.notion_token
    if not token:
        return {"error": "NOTION_TOKEN not configured", "events_stored": 0}

    sync_started_at = datetime.now(timezone.utc)
    since = _last_sync_at
    user_cache: dict[str, str] = {}
    events: list[ActivityEvent] = []

    with httpx.Client() as client:
        has_more = True
        cursor = None
        done = False

        while has_more and not done:
            body: dict = {
                "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                "page_size": 100,
            }
            if cursor:
                body["start_cursor"] = cursor

            resp = client.post(
                f"{_NOTION_API}/search",
                headers=_headers(token),
                json=body,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for page in data.get("results", []):
                last_edited_str = page.get("last_edited_time", "")
                if not last_edited_str:
                    continue

                edited_at = datetime.fromisoformat(last_edited_str.replace("Z", "+00:00"))

                if since and edited_at <= since:
                    done = True
                    break

                created_str = page.get("created_time", "")
                event_type = "page_created" if created_str == last_edited_str else "page_edited"

                actor_id = (page.get("last_edited_by") or {}).get("id", "")
                actor = _resolve_user(client, token, actor_id, user_cache) if actor_id else ""

                events.append(ActivityEvent(
                    source="notion",
                    event_type=event_type,
                    actor=actor,
                    repo="notion",
                    title=_page_title(page),
                    url=page.get("url"),
                    metadata={"page_id": page.get("id")},
                ))

            has_more = data.get("has_more", False) and not done
            cursor = data.get("next_cursor")

    if events:
        supabase = get_supabase()
        supabase.table("activity_events").insert([e.model_dump() for e in events]).execute()
        logger.info("Notion sync stored %d events", len(events))

    _last_sync_at = sync_started_at
    _last_sync = {
        "ran_at": sync_started_at.isoformat(),
        "events_stored": len(events),
    }
    return _last_sync
