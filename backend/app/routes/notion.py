from fastapi import APIRouter, HTTPException, status

from app.services.notion import sync_notion, _last_sync

router = APIRouter(prefix="/notion", tags=["notion"])


@router.get("/status")
def notion_status():
    return {"last_sync": _last_sync}


@router.post("/sync")
def notion_sync():
    result = sync_notion()
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"])
    return result
