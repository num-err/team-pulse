import json

from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.integrations.supabase_client import get_supabase
from app.models.activity_event import ActivityEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_passcode(payload_passcode: str, secret: str) -> None:
    if payload_passcode != secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid passcode")


def _normalize_comment(payload: dict) -> ActivityEvent:
    comment_parts = payload.get("comment", [])
    text = " ".join(p.get("text", "") for p in comment_parts if isinstance(p, dict)).strip()

    triggered_by = payload.get("triggered_by") or {}
    return ActivityEvent(
        source="figma",
        event_type="file_comment",
        actor=triggered_by.get("handle", ""),
        repo=payload.get("file_name", ""),
        title=text[:120] or None,
        url=f"https://www.figma.com/file/{payload.get('file_key')}",
        metadata={
            "file_key": payload.get("file_key"),
            "comment_id": payload.get("comment_id"),
            "parent_id": payload.get("parent_id"),
        },
    )


def _normalize_version(payload: dict) -> ActivityEvent:
    triggered_by = payload.get("triggered_by") or {}
    label = payload.get("label") or payload.get("description") or "Unnamed version"
    return ActivityEvent(
        source="figma",
        event_type="version_saved",
        actor=triggered_by.get("handle", ""),
        repo=payload.get("file_name", ""),
        title=label,
        url=f"https://www.figma.com/file/{payload.get('file_key')}",
        metadata={
            "file_key": payload.get("file_key"),
            "version_id": payload.get("version_id"),
            "description": payload.get("description"),
        },
    )


@router.post("/figma", status_code=status.HTTP_204_NO_CONTENT)
async def figma_webhook(request: Request):
    body = await request.body()
    payload = json.loads(body)

    settings = get_settings()
    if settings.figma_webhook_passcode:
        _verify_passcode(payload.get("passcode", ""), settings.figma_webhook_passcode)

    event_type = payload.get("event_type")

    if event_type == "PING":
        return

    event: ActivityEvent | None = None
    if event_type == "FILE_COMMENT":
        event = _normalize_comment(payload)
    elif event_type == "FILE_VERSION_UPDATE":
        event = _normalize_version(payload)

    if event:
        supabase = get_supabase()
        supabase.table("activity_events").insert(event.model_dump()).execute()
