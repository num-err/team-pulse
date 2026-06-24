import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings
from app.integrations.supabase_client import get_supabase
from app.models.activity_event import ActivityEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_signature(body: bytes, signature_header: str, secret: str) -> None:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


def _normalize_pr(payload: dict) -> ActivityEvent | None:
    action = payload.get("action")
    pr = payload.get("pull_request", {})

    if action == "opened":
        event_type = "pr_opened"
    elif action == "closed" and pr.get("merged"):
        event_type = "pr_merged"
    elif action == "closed":
        event_type = "pr_closed"
    else:
        return None

    repo = payload.get("repository", {})
    return ActivityEvent(
        source="github",
        event_type=event_type,
        actor=pr.get("user", {}).get("login", ""),
        repo=repo.get("full_name", ""),
        title=pr.get("title"),
        url=pr.get("html_url"),
        metadata={
            "pr_number": pr.get("number"),
            "base": pr.get("base", {}).get("ref"),
            "head": pr.get("head", {}).get("ref"),
            "draft": pr.get("draft", False),
        },
    )


def _normalize_push(payload: dict) -> list[ActivityEvent]:
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "")
    pusher = payload.get("pusher", {}).get("name", "")
    ref = payload.get("ref", "")

    events = []
    for commit in payload.get("commits", []):
        message = commit.get("message", "").splitlines()[0]
        events.append(
            ActivityEvent(
                source="github",
                event_type="commit_pushed",
                actor=commit.get("author", {}).get("username") or pusher,
                repo=repo_name,
                title=message,
                url=commit.get("url"),
                metadata={
                    "sha": commit.get("id"),
                    "ref": ref,
                    "added": commit.get("added", []),
                    "modified": commit.get("modified", []),
                },
            )
        )
    return events


@router.post("/github", status_code=status.HTTP_204_NO_CONTENT)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: str = Header(None),
):
    body = await request.body()

    settings = get_settings()
    if settings.github_webhook_secret:
        if not x_hub_signature_256:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")
        _verify_signature(body, x_hub_signature_256, settings.github_webhook_secret)

    if x_github_event == "ping":
        return

    payload = json.loads(body)
    events: list[ActivityEvent] = []

    if x_github_event == "pull_request":
        event = _normalize_pr(payload)
        if event:
            events.append(event)
    elif x_github_event == "push":
        events.extend(_normalize_push(payload))

    if events:
        supabase = get_supabase()
        supabase.table("activity_events").insert(
            [e.model_dump() for e in events]
        ).execute()
