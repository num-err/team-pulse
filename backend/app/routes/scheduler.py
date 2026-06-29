from fastapi import APIRouter

from app.services.scheduler import get_last_run, run_daily_digests

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status")
def scheduler_status():
    last = get_last_run()
    return {
        "last_run": last,
        "message": "No runs yet this session." if last is None else "OK",
    }


@router.post("/run-now")
def trigger_now():
    result = run_daily_digests()
    return result
