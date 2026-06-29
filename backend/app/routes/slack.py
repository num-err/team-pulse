from fastapi import APIRouter, HTTPException, Query, status

from app.services.digest import generate_digest
from app.services.slack import post_digest

router = APIRouter(prefix="/slack", tags=["slack"])


@router.post("/deliver")
def deliver_digest(
    actor: str = Query(..., description="GitHub username to summarize and deliver"),
    channel: str = Query(None, description="Slack channel override (e.g. #team-updates)"),
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
