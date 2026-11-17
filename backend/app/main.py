import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import digest, health, notion, scheduler, slack, workspaces
from app.routes.webhooks import figma as figma_webhook
from app.routes.webhooks import github as github_webhook
from app.routes.webhooks import linear as linear_webhook
from app.services.scheduler import run_due_workspaces

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler = BackgroundScheduler(timezone=timezone.utc)
    # One tick checks every workspace against its own local digest time
    # (see services/scheduler.py). next_run_time=now also runs it at boot,
    # which is what catches up after the process was down across a team's
    # scheduled time.
    _scheduler.add_job(
        run_due_workspaces,
        "interval",
        minutes=settings.scheduler_tick_minutes,
        id="digest_tick",
        next_run_time=datetime.now(timezone.utc),
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    yield
    _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Team Pulse API",
    description="Backend for Team Pulse — a zero-input async standup tool.",
    version="0.2.0",
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
app.include_router(workspaces.router)
app.include_router(digest.router)
app.include_router(slack.router)
app.include_router(scheduler.router)
app.include_router(notion.router)
app.include_router(github_webhook.router)
app.include_router(linear_webhook.router)
app.include_router(figma_webhook.router)


@app.get("/")
def root():
    return {"name": "Team Pulse API", "version": app.version}
