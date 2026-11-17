"""Account + workspace management: who am I, my workspaces, settings, and
per-workspace integration setup."""
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.auth import CurrentUser, get_current_user
from app.config import get_settings
from app.deps import Membership, require_admin, require_member
from app.services import workspaces as ws

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])


# --------------------------------------------------------------------- models


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    timezone: str = "UTC"


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    timezone: str | None = None
    digest_hour: int | None = Field(None, ge=0, le=23)
    digest_minute: int | None = Field(None, ge=0, le=59)


class SlackSetup(BaseModel):
    bot_token: str = Field(..., pattern=r"^xoxb-")
    channel: str = Field(..., pattern=r"^[CG][A-Z0-9]{6,}$", description="Channel ID, e.g. C0123ABCD (not #name)")


class NotionSetup(BaseModel):
    token: str = Field(..., min_length=10)


# ---------------------------------------------------------------------- me


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {
        "user": {"id": user.id, "email": user.email},
        "workspaces": ws.list_workspaces_for_user(user.id),
    }


# --------------------------------------------------------------- workspaces


@router.get("/workspaces")
def list_my_workspaces(user: CurrentUser = Depends(get_current_user)):
    return {"workspaces": ws.list_workspaces_for_user(user.id)}


@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
def create_workspace(body: WorkspaceCreate, user: CurrentUser = Depends(get_current_user)):
    try:
        return ws.create_workspace(user.id, body.name, body.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/workspaces/{workspace_id}")
def get_workspace(m: Membership = Depends(require_member)):
    return {**ws.get_workspace(m.workspace_id), "role": m.role}


@router.patch("/workspaces/{workspace_id}")
def update_workspace(body: WorkspaceUpdate, m: Membership = Depends(require_admin)):
    try:
        updated = ws.update_workspace(m.workspace_id, body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {**updated, "role": m.role}


# ------------------------------------------------------------- integrations


def _webhook_url(provider: str, workspace_id: str) -> str:
    return f"{get_settings().public_api_url.rstrip('/')}/webhooks/{provider}/{workspace_id}"


@router.get("/workspaces/{workspace_id}/integrations")
def list_integrations(m: Membership = Depends(require_member)):
    items = ws.list_integrations(m.workspace_id)
    for item in items:
        if item["provider"] in ws.WEBHOOK_PROVIDERS:
            item["webhook_url"] = _webhook_url(item["provider"], m.workspace_id)
    return {"integrations": items}


@router.post("/workspaces/{workspace_id}/integrations/{provider}/webhook")
def setup_webhook(provider: Literal["github", "linear", "figma"], m: Membership = Depends(require_admin)):
    """Create (or rotate) this workspace's webhook signing secret for a source.

    The secret is returned exactly once — paste it into the source's webhook
    settings along with the URL. Rotating invalidates the previous secret.
    """
    secret = ws.new_webhook_secret()
    ws.upsert_integration(m.workspace_id, provider, {"webhook_secret": secret}, {})
    return {"provider": provider, "webhook_url": _webhook_url(provider, m.workspace_id), "secret": secret}


@router.put("/workspaces/{workspace_id}/integrations/slack")
def setup_slack(body: SlackSetup, m: Membership = Depends(require_admin)):
    """Connect Slack with a bot token + channel ID. Validates the token first."""
    try:
        auth = WebClient(token=body.bot_token).auth_test()
    except SlackApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slack rejected the token: {exc.response['error']}"
        ) from exc
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not reach Slack") from exc
    settings = {"channel": body.channel, "team": auth.get("team"), "team_id": auth.get("team_id")}
    ws.upsert_integration(m.workspace_id, "slack", {"bot_token": body.bot_token}, settings)
    return {"provider": "slack", "connected": True, "settings": settings}


@router.put("/workspaces/{workspace_id}/integrations/notion")
def setup_notion(body: NotionSetup, m: Membership = Depends(require_admin)):
    ws.upsert_integration(m.workspace_id, "notion", {"token": body.token}, {})
    return {"provider": "notion", "connected": True, "settings": {}}


@router.delete("/workspaces/{workspace_id}/integrations/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(provider: Literal["github", "linear", "figma", "notion", "slack"], m: Membership = Depends(require_admin)):
    ws.delete_integration(m.workspace_id, provider)
