from fastapi import APIRouter, Depends

from app.config import get_settings
from app.deps import require_api_key
from app.services.health import classify_team_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Liveness check. Reports basic service status."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "team-pulse-api",
        "env": settings.app_env,
        "supabase_configured": bool(settings.supabase_url and settings.supabase_key),
    }


@router.get("/health/team", dependencies=[Depends(require_api_key)])
def health_team():
    """Per-actor health classification: HEALTHY / THRASHING / SILENT_STUCK / IDLE."""
    return {"actors": classify_team_health()}
