from pydantic import BaseModel


class ActivityEvent(BaseModel):
    source: str
    event_type: str
    actor: str
    repo: str
    title: str | None = None
    url: str | None = None
    metadata: dict | None = None
