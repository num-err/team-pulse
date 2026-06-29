import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings
from app.integrations.supabase_client import get_supabase
from app.models.activity_event import ActivityEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_STATE_TYPE_TO_EVENT = {
    "started": "issue_started",
    "completed": "issue_completed",
    "cancelled": "issue_cancelled",
}


def _verify_signature(body: bytes, signature_header: str, secret: str) -> None:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


def _actor_name(user: dict | None) -> str:
    if not user:
        return ""
    return user.get("displayName") or user.get("name") or ""


def _normalize_issue(action: str, data: dict) -> ActivityEvent | None:
    if action == "create":
        event_type = "issue_created"
        actor = _actor_name(data.get("creator"))
    elif action == "update":
        state = data.get("state") or {}
        event_type = _STATE_TYPE_TO_EVENT.get(state.get("type", ""), "issue_updated")
        actor = _actor_name(data.get("assignee") or data.get("creator"))
    else:
        return None

    team = data.get("team") or {}
    return ActivityEvent(
        source="linear",
        event_type=event_type,
        actor=actor,
        repo=team.get("key") or team.get("name") or "",
        title=data.get("title"),
        url=data.get("url"),
        metadata={
            "identifier": data.get("identifier"),
            "priority": data.get("priority"),
            "state": (data.get("state") or {}).get("name"),
        },
    )


def _normalize_comment(action: str, data: dict) -> ActivityEvent | None:
    if action != "create":
        return None

    issue = data.get("issue") or {}
    team = issue.get("team") or {}
    body = data.get("body") or ""
    return ActivityEvent(
        source="linear",
        event_type="comment_added",
        actor=_actor_name(data.get("user")),
        repo=team.get("key") or team.get("name") or "",
        title=body[:120] or None,
        url=data.get("url"),
        metadata={
            "issue_identifier": issue.get("identifier"),
            "issue_title": issue.get("title"),
        },
    )


@router.post("/linear", status_code=status.HTTP_204_NO_CONTENT)
async def linear_webhook(
    request: Request,
    linear_signature: str = Header(None),
):
    body = await request.body()

    settings = get_settings()
    if settings.linear_webhook_secret:
        if not linear_signature:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")
        _verify_signature(body, linear_signature, settings.linear_webhook_secret)

    payload = json.loads(body)
    event_type = payload.get("type")
    action = payload.get("action")
    data = payload.get("data", {})

    event: ActivityEvent | None = None
    if event_type == "Issue":
        event = _normalize_issue(action, data)
    elif event_type == "Comment":
        event = _normalize_comment(action, data)

    if event:
        supabase = get_supabase()
        supabase.table("activity_events").insert(event.model_dump()).execute()
