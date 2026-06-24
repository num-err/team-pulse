from datetime import datetime

from pydantic import BaseModel


class StandupEntry(BaseModel):
    """A single auto-generated async standup update for a team member."""

    id: str
    user_id: str
    team_id: str
    summary: str
    created_at: datetime
