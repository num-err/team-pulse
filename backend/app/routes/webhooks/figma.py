import hmac
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.models.activity_event import ActivityEvent
from app.routes.webhooks.common import store_events, webhook_secret_for

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_passcode(payload_passcode: str, secret: str) -> None:
    if not hmac.compare_digest(str(payload_passcode), secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid passcode")


def _normalize_comment(payload: dict) -> ActivityEvent:
    comment_parts = payload.get("comment", [])
    text = " ".join(p.get("text", "") for p in comment_parts if isinstance(p, dict)).strip()

    triggered_by = payload.get("triggered_by") or {}
    comment_id = payload.get("comment_id")
    return ActivityEvent(
        source="figma",
        event_type="file_comment",
        actor=triggered_by.get("handle", ""),
        repo=payload.get("file_name", ""),
        title=text[:120] or None,
        url=f"https://www.figma.com/file/{payload.get('file_key')}",
        metadata={
            "file_key": payload.get("file_key"),
            "comment_id": comment_id,
            "parent_id": payload.get("parent_id"),
        },
        dedup_key=f"figma:comment:{comment_id}",
    )


def _normalize_version(payload: dict) -> ActivityEvent:
    triggered_by = payload.get("triggered_by") or {}
    label = payload.get("label") or payload.get("description") or "Unnamed version"
    version_id = payload.get("version_id")
    return ActivityEvent(
        source="figma",
        event_type="version_saved",
        actor=triggered_by.get("handle", ""),
        repo=payload.get("file_name", ""),
        title=label,
        url=f"https://www.figma.com/file/{payload.get('file_key')}",
        metadata={
            "file_key": payload.get("file_key"),
            "version_id": version_id,
            "description": payload.get("description"),
        },
        dedup_key=f"figma:version:{version_id}",
    )


@router.post("/figma/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def figma_webhook(workspace_id: UUID, request: Request):
    body = await request.body()
    payload = json.loads(body)

    _verify_passcode(payload.get("passcode", ""), webhook_secret_for(workspace_id, "figma"))

    event_type = payload.get("event_type")

    if event_type == "PING":
        return

    event: ActivityEvent | None = None
    if event_type == "FILE_COMMENT":
        event = _normalize_comment(payload)
    elif event_type == "FILE_VERSION_UPDATE":
        event = _normalize_version(payload)

    if event:
        store_events(workspace_id, [event])
