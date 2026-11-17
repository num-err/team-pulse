"""Shared webhook plumbing: workspace lookup, secret retrieval, storage.

Each workspace gets its own webhook URL per source —
`/webhooks/{source}/{workspace_id}` — and its own signing secret, stored in
workspace_integrations.credentials["webhook_secret"]. A workspace without a
configured secret rejects every delivery: unsigned ingestion is never
allowed, in any environment.
"""
from uuid import UUID

from fastapi import HTTPException, status

from app.integrations.supabase_client import get_supabase
from app.models.activity_event import ActivityEvent
from app.services.identity import resolve_actor
from app.services.workspaces import get_integration, get_workspace


def webhook_secret_for(workspace_id: UUID, provider: str) -> str:
    ws_id = str(workspace_id)
    if get_workspace(ws_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown workspace")
    integration = get_integration(ws_id, provider) or {}
    secret = (integration.get("credentials") or {}).get("webhook_secret")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{provider} webhooks aren't set up for this workspace",
        )
    return secret


def store_events(workspace_id: UUID, events: list[ActivityEvent]) -> None:
    """Stamp the workspace, resolve identities, and idempotently upsert."""
    if not events:
        return
    ws_id = str(workspace_id)
    for e in events:
        e.workspace_id = ws_id
        e.actor = resolve_actor(ws_id, e.source, e.actor)
    get_supabase().table("activity_events").upsert(
        [e.model_dump() for e in events],
        on_conflict="workspace_id,dedup_key",
        ignore_duplicates=True,
    ).execute()
