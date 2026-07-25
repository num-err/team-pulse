import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings
from app.integrations.supabase_client import get_supabase
from app.models.activity_event import ActivityEvent
from app.services.identity import resolve_actor

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
    repo_name = repo.get("full_name", "")
    pr_number = pr.get("number")
    return ActivityEvent(
        source="github",
        event_type=event_type,
        actor=pr.get("user", {}).get("login", ""),
        repo=repo_name,
        title=pr.get("title"),
        url=pr.get("html_url"),
        metadata={
            "pr_number": pr_number,
            "base": pr.get("base", {}).get("ref"),
            "head": pr.get("head", {}).get("ref"),
            "draft": pr.get("draft", False),
        },
        # PR number + event_type is stable across GitHub's own webhook retries
        # (redelivery of the same "opened"/"closed" action for the same PR).
        dedup_key=f"github:pr:{repo_name}:{pr_number}:{event_type}",
    )


def _normalize_push(payload: dict) -> list[ActivityEvent]:
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "")
    pusher = payload.get("pusher", {}).get("name", "")
    ref = payload.get("ref", "")

    events = []
    for commit in payload.get("commits", []):
        message = commit.get("message", "").splitlines()[0]
        sha = commit.get("id")
        events.append(
            ActivityEvent(
                source="github",
                event_type="commit_pushed",
                actor=commit.get("author", {}).get("username") or pusher,
                repo=repo_name,
                title=message,
                url=commit.get("url"),
                metadata={
                    "sha": sha,
                    "ref": ref,
                    "added": commit.get("added", []),
                    "modified": commit.get("modified", []),
                },
                # Commit SHA is already globally stable — no event_type needed.
                dedup_key=f"github:commit:{repo_name}:{sha}",
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
        for e in events:
            e.actor = resolve_actor(e.source, e.actor)
        supabase = get_supabase()
        supabase.table("activity_events").upsert(
            [e.model_dump() for e in events],
            on_conflict="dedup_key",
            ignore_duplicates=True,
        ).execute()
