from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import health, digest
from app.routes.webhooks import github as github_webhook

settings = get_settings()

app = FastAPI(
    title="Team Pulse API",
    description="Backend for Team Pulse — a zero-input async standup tool.",
    version="0.1.0",
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


@app.get("/")
def root():
    return {"name": "Team Pulse API", "version": app.version}
