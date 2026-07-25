from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import require_api_key
from app.services.notion import get_last_sync, sync_notion

router = APIRouter(prefix="/notion", tags=["notion"], dependencies=[Depends(require_api_key)])


@router.get("/status")
def notion_status():
    return {"last_sync": get_last_sync()}


@router.post("/sync")
def notion_sync():
    result = sync_notion()
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"])
    return result
