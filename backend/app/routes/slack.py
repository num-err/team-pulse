from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import require_api_key
from app.services.digest import generate_digest
from app.services.slack import post_digest, post_team_digest
from app.services.team_digest import generate_team_digest

router = APIRouter(prefix="/slack", tags=["slack"])


@router.post("/deliver", dependencies=[Depends(require_api_key)])
def deliver_digest(
    actor: str = Query(..., description="GitHub username to summarize and deliver"),
    channel: str = Query(None, description="Slack channel override"),
):
    digest = generate_digest(actor)

    try:
        ts = post_digest(digest, channel=channel)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Slack error: {exc}",
        ) from exc

    return {**digest, "slack_ts": ts, "delivered": True}


@router.post("/deliver-team", dependencies=[Depends(require_api_key)])
def deliver_team_digest(
    channel: str = Query(None, description="Slack channel override"),
):
    team_digest = generate_team_digest()

    try:
        ts = post_team_digest(team_digest, channel=channel)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Slack error: {exc}",
        ) from exc

    return {**team_digest, "slack_ts": ts, "delivered": True}
