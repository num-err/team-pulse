from fastapi import APIRouter, Depends

from app.deps import Membership, require_admin, require_member
from app.services.scheduler import get_last_run, run_workspace_digest

router = APIRouter(prefix="/workspaces/{workspace_id}/scheduler", tags=["scheduler"])


@router.get("/status")
def scheduler_status(m: Membership = Depends(require_member)):
    last = get_last_run(m.workspace_id)
    return {"last_run": last, "message": "No runs yet." if last is None else "OK"}


@router.post("/run-now")
def trigger_now(m: Membership = Depends(require_admin)):
    """Generate and post today's team digest immediately. Counts as today's
    run, so the scheduled one won't post again later the same day."""
    return run_workspace_digest(m.workspace_id)
