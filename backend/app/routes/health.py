from fastapi import APIRouter

from app.config import get_settings

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
