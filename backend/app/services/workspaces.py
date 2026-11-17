"""Workspaces, membership, and per-workspace integration config.

A workspace is one team. Every row of activity data belongs to exactly one
workspace, and every user-facing route is scoped to a workspace the caller
is a member of (see app.deps.require_member).
"""
import secrets
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.integrations.supabase_client import get_supabase

ROLES = ("owner", "admin", "member")
ADMIN_ROLES = {"owner", "admin"}
PROVIDERS = ("github", "linear", "figma", "notion", "slack")
WEBHOOK_PROVIDERS = {"github", "linear", "figma"}

_WORKSPACE_FIELDS = "id, name, timezone, digest_hour, digest_minute, created_at"


def validate_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown timezone: {name!r}") from exc
    return name


# ------------------------------------------------------------------ workspaces


def create_workspace(user_id: str, name: str, tz: str = "UTC") -> dict:
    """Create a workspace and make `user_id` its owner."""
    supabase = get_supabase()
    result = (
        supabase.table("workspaces")
        .insert({"name": name.strip(), "timezone": validate_timezone(tz), "created_by": user_id})
        .execute()
    )
    workspace = result.data[0]
    supabase.table("workspace_members").insert(
        {"workspace_id": workspace["id"], "user_id": user_id, "role": "owner"}
    ).execute()
    return {**_public(workspace), "role": "owner"}


def list_workspaces_for_user(user_id: str) -> list[dict]:
    supabase = get_supabase()
    memberships = (
        supabase.table("workspace_members").select("workspace_id, role").eq("user_id", user_id).execute().data or []
    )
    if not memberships:
        return []
    role_by_id = {m["workspace_id"]: m["role"] for m in memberships}
    workspaces = (
        supabase.table("workspaces")
        .select(_WORKSPACE_FIELDS)
        .in_("id", list(role_by_id))
        .order("created_at")
        .execute()
        .data
        or []
    )
    return [{**_public(w), "role": role_by_id[w["id"]]} for w in workspaces]


def get_workspace(workspace_id: str) -> dict | None:
    rows = get_supabase().table("workspaces").select(_WORKSPACE_FIELDS).eq("id", workspace_id).limit(1).execute().data
    return _public(rows[0]) if rows else None


def list_all_workspaces() -> list[dict]:
    """Every workspace — for the scheduler only, never exposed via the API."""
    return [_public(w) for w in (get_supabase().table("workspaces").select(_WORKSPACE_FIELDS).execute().data or [])]


def update_workspace(workspace_id: str, changes: dict) -> dict:
    allowed = {k: v for k, v in changes.items() if k in {"name", "timezone", "digest_hour", "digest_minute"}}
    if "timezone" in allowed:
        validate_timezone(allowed["timezone"])
    if "name" in allowed:
        allowed["name"] = allowed["name"].strip()
    if allowed:
        get_supabase().table("workspaces").update(allowed).eq("id", workspace_id).execute()
    return get_workspace(workspace_id)


def _public(row: dict) -> dict:
    return {k: row.get(k) for k in ("id", "name", "timezone", "digest_hour", "digest_minute", "created_at")}


# ------------------------------------------------------------------ membership


def get_role(workspace_id: str, user_id: str) -> str | None:
    rows = (
        get_supabase()
        .table("workspace_members")
        .select("role")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0]["role"] if rows else None


# ---------------------------------------------------------------- integrations


def get_integration(workspace_id: str, provider: str) -> dict | None:
    """Full integration row INCLUDING secrets — server-side use only."""
    rows = (
        get_supabase()
        .table("workspace_integrations")
        .select("provider, credentials, settings, updated_at")
        .eq("workspace_id", workspace_id)
        .eq("provider", provider)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def list_integrations(workspace_id: str) -> list[dict]:
    """Connection status per provider, with secrets stripped."""
    rows = (
        get_supabase()
        .table("workspace_integrations")
        .select("provider, settings, updated_at")
        .eq("workspace_id", workspace_id)
        .execute()
        .data
        or []
    )
    by_provider = {r["provider"]: r for r in rows}
    return [
        {
            "provider": p,
            "connected": p in by_provider,
            "settings": (by_provider.get(p) or {}).get("settings") or {},
            "updated_at": (by_provider.get(p) or {}).get("updated_at"),
        }
        for p in PROVIDERS
    ]


def upsert_integration(workspace_id: str, provider: str, credentials: dict, settings: dict) -> None:
    get_supabase().table("workspace_integrations").upsert(
        {
            "workspace_id": workspace_id,
            "provider": provider,
            "credentials": credentials,
            "settings": settings,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="workspace_id,provider",
    ).execute()


def delete_integration(workspace_id: str, provider: str) -> None:
    (
        get_supabase()
        .table("workspace_integrations")
        .delete()
        .eq("workspace_id", workspace_id)
        .eq("provider", provider)
        .execute()
    )


def new_webhook_secret() -> str:
    return secrets.token_urlsafe(32)
