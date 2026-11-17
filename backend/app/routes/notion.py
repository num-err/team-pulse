from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import Membership, require_admin, require_member
from app.services.notion import get_last_sync, sync_notion

router = APIRouter(prefix="/workspaces/{workspace_id}/notion", tags=["notion"])


@router.get("/status")
def notion_status(m: Membership = Depends(require_member)):
    return {"last_sync": get_last_sync(m.workspace_id)}


@router.post("/sync")
def notion_sync(m: Membership = Depends(require_admin)):
    result = sync_notion(m.workspace_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result["error"])
    return result
