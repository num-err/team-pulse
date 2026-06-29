from fastapi import APIRouter, Query

from app.services.digest import generate_digest

router = APIRouter(prefix="/digest", tags=["digest"])


@router.post("/generate")
def generate_digest_route(actor: str = Query(..., description="GitHub username to summarize")):
    return generate_digest(actor)
