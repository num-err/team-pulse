from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import health, digest, slack, scheduler
from app.routes.webhooks import github as github_webhook
from app.services.scheduler import run_daily_digests

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_daily_digests,
        "cron",
        hour=settings.digest_cron_hour,
        minute=settings.digest_cron_minute,
        id="daily_digest",
    )
    _scheduler.start()
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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(github_webhook.router)
app.include_router(digest.router)
app.include_router(slack.router)
app.include_router(scheduler.router)


@app.get("/")
def root():
    return {"name": "Team Pulse API", "version": app.version}
