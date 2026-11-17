from pydantic import BaseModel


class ActivityEvent(BaseModel):
    # Set at ingestion from the webhook URL / sync job; every stored row has one.
    workspace_id: str | None = None
    source: str
    event_type: str
    actor: str
    repo: str
    title: str | None = None
    url: str | None = None
    metadata: dict | None = None
    # Natural per-source idempotency key (e.g. "github:pr:owner/repo:123:pr_merged").
    # None for events where a stable key can't be derived — that's fine, the DB
    # unique constraint allows multiple NULLs. See webhook idempotency in CLAUDE.md.
    dedup_key: str | None = None
