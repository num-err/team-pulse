import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import health, digest, slack, scheduler, notion
from app.routes.webhooks import github as github_webhook
from app.routes.webhooks import figma as figma_webhook
from app.routes.webhooks import linear as linear_webhook
from app.services.notion import sync_notion
from app.services.scheduler import MISFIRE_GRACE_SECONDS, catch_up_if_missed, run_daily_digests

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_daily_digests,
        "cron",
        hour=settings.digest_cron_hour,
        minute=settings.digest_cron_minute,
        id="daily_digest",
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )
    _scheduler.add_job(
        sync_notion,
        "cron",
        hour=settings.digest_cron_hour,
        minute=max(0, settings.digest_cron_minute - 5),
        id="notion_sync",
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )
    _scheduler.start()
    try:
        # Covers a full process restart spanning the scheduled time, which
        # misfire_grace_time above does not — a brand new scheduler has no
        # memory of a cron tick it never got the chance to register.
        catch_up_if_missed()
    except Exception:
        logger.exception("Startup catch-up check failed")
    yield
    _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Team Pulse API",
    description="Backend for Team Pulse — a zero-input async standup tool.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(github_webhook.router)
app.include_router(notion.router)
app.include_router(linear_webhook.router)
app.include_router(figma_webhook.router)
app.include_router(digest.router)
app.include_router(slack.router)
app.include_router(scheduler.router)


@app.get("/")
def root():
    return {"name": "Team Pulse API", "version": app.version}
