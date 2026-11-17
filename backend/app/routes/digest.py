from fastapi import APIRouter, Depends, Query

from app.deps import Membership, require_member
from app.services.digest import generate_digest
from app.services.team_digest import generate_team_digest

router = APIRouter(prefix="/workspaces/{workspace_id}/digest", tags=["digest"])


@router.post("/generate")
def generate_digest_route(
    actor: str = Query(..., description="Person to summarize (canonical name or handle)"),
    m: Membership = Depends(require_member),
):
    return generate_digest(m.workspace_id, actor)


@router.post("/team")
def generate_team_digest_route(m: Membership = Depends(require_member)):
    return generate_team_digest(m.workspace_id)
