from fastapi import APIRouter, Depends

from app.config import get_settings
from app.deps import Membership, require_member
from app.services.health import classify_team_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Liveness check. Public; reports basic service status only."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "team-pulse-api",
        "env": settings.app_env,
        "supabase_configured": bool(settings.supabase_url and settings.supabase_key),
    }


@router.get("/workspaces/{workspace_id}/health/team")
def health_team(m: Membership = Depends(require_member)):
    """Per-person health classification: HEALTHY / THRASHING / SILENT_STUCK / IDLE."""
    return {"actors": classify_team_health(m.workspace_id)}
