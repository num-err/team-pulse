from fastapi import APIRouter, Depends, Query

from app.deps import require_api_key
from app.services.digest import generate_digest
from app.services.team_digest import generate_team_digest

router = APIRouter(prefix="/digest", tags=["digest"])


@router.post("/generate", dependencies=[Depends(require_api_key)])
def generate_digest_route(actor: str = Query(..., description="GitHub username to summarize")):
    return generate_digest(actor)


@router.post("/team", dependencies=[Depends(require_api_key)])
def generate_team_digest_route():
    return generate_team_digest()
