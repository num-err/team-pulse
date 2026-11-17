from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import Membership, require_member
from app.services.digest import generate_digest
from app.services.slack import SlackNotConfigured, post_digest, post_team_digest, slack_destination
from app.services.team_digest import generate_team_digest

router = APIRouter(prefix="/workspaces/{workspace_id}/slack", tags=["slack"])

_CHANNEL_PATTERN = r"^[CG][A-Z0-9]{6,}$"


def _destination(workspace_id: str, channel: str | None):
    try:
        return slack_destination(workspace_id, channel)
    except SlackNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/deliver")
def deliver_digest(
    actor: str = Query(..., description="Person to summarize and deliver"),
    channel: str | None = Query(None, pattern=_CHANNEL_PATTERN, description="Slack channel ID override"),
    m: Membership = Depends(require_member),
):
    dest = _destination(m.workspace_id, channel)
    digest = generate_digest(m.workspace_id, actor)
    try:
        ts = post_digest(digest, dest)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Slack error: {exc}") from exc
    return {**digest, "slack_ts": ts, "delivered": True}


@router.post("/deliver-team")
def deliver_team_digest(
    channel: str | None = Query(None, pattern=_CHANNEL_PATTERN, description="Slack channel ID override"),
    m: Membership = Depends(require_member),
):
    dest = _destination(m.workspace_id, channel)
    team_digest = generate_team_digest(m.workspace_id)
    try:
        ts = post_team_digest(team_digest, dest)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Slack error: {exc}") from exc
    return {**team_digest, "slack_ts": ts, "delivered": True}
