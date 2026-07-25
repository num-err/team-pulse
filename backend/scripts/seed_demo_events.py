"""Seed fresh cross-tool activity_events rows for live demos.

The dashboard only looks at the last 24h, and real Linear/Notion/Figma
activity doesn't happen on demand. Run this shortly before a demo so
"Generate team digest" shows a coherent multi-tool story instead of
GitHub-only.

Usage:
    .venv/bin/python scripts/seed_demo_events.py
"""

from datetime import datetime, timedelta, timezone

from app.integrations.supabase_client import get_supabase

now = datetime.now(timezone.utc)


def hours_ago(h: float) -> str:
    return (now - timedelta(hours=h)).isoformat()


EVENTS = [
    # --- num-err: fixes the login auth bug across GitHub, Linear, Figma ---
    {
        "source": "github",
        "event_type": "commit_pushed",
        "actor": "num-err",
        "repo": "num-err/team-pulse",
        "title": "Fix session token expiry check in login flow",
        "url": "https://github.com/num-err/team-pulse/commit/demo1",
        "metadata": {"demo_seed": True},
        "received_at": hours_ago(6),
    },
    {
        "source": "linear",
        "event_type": "issue_started",
        "actor": "num-err",
        "repo": "ENG",
        "title": "Fix authentication bug on login page",
        "url": "https://linear.app/team-pulse/issue/ENG-101",
        "metadata": {"identifier": "ENG-101", "state": "In Progress", "demo_seed": True},
        "received_at": hours_ago(5.5),
    },
    {
        "source": "github",
        "event_type": "pr_opened",
        "actor": "num-err",
        "repo": "num-err/team-pulse",
        "title": "Fix auth bug in login flow",
        "url": "https://github.com/num-err/team-pulse/pull/12",
        "metadata": {"demo_seed": True},
        "received_at": hours_ago(5),
    },
    {
        "source": "figma",
        "event_type": "file_comment",
        "actor": "num-err",
        "repo": "Mobile App Design",
        "title": "Verified spacing matches the new auth error state",
        "url": "https://www.figma.com/file/demo",
        "metadata": {"demo_seed": True},
        "received_at": hours_ago(3),
    },
    {
        "source": "linear",
        "event_type": "issue_completed",
        "actor": "num-err",
        "repo": "ENG",
        "title": "Fix authentication bug on login page",
        "url": "https://linear.app/team-pulse/issue/ENG-101",
        "metadata": {"identifier": "ENG-101", "state": "Done", "demo_seed": True},
        "received_at": hours_ago(2),
    },
    # --- Numer Ahmed: docs + review pass ---
    {
        "source": "notion",
        "event_type": "page_edited",
        "actor": "Numer Ahmed",
        "repo": "notion",
        "title": "Team Pulse — Pitch Deck",
        "url": "https://notion.so/demo-pitch-deck",
        "metadata": {"demo_seed": True},
        "received_at": hours_ago(4),
    },
    {
        "source": "linear",
        "event_type": "comment_added",
        "actor": "Numer Ahmed",
        "repo": "ENG",
        "title": "Confirmed fix in staging, looks solid",
        "url": "https://linear.app/team-pulse/issue/ENG-101",
        "metadata": {"issue_identifier": "ENG-101", "demo_seed": True},
        "received_at": hours_ago(1),
    },
    {
        "source": "notion",
        "event_type": "page_edited",
        "actor": "Numer Ahmed",
        "repo": "notion",
        "title": "GTM Strategy Notes",
        "url": "https://notion.so/demo-gtm-notes",
        "metadata": {"demo_seed": True},
        "received_at": hours_ago(0.5),
    },
    # --- Ada Chen: design, active today via Figma, PLUS a deliberately
    # stale Linear issue (started >48h ago, nothing since) to exercise
    # the blocker alert during the demo. ---
    {
        "source": "figma",
        "event_type": "version_saved",
        "actor": "Ada Chen",
        "repo": "Payment UI",
        "title": "Payment UI v3",
        "url": "https://www.figma.com/file/demo-payment-ui",
        "metadata": {"demo_seed": True},
        "received_at": hours_ago(2.5),
    },
    {
        "source": "linear",
        "event_type": "issue_started",
        "actor": "Ada Chen",
        "repo": "DESIGN",
        "title": "Payment UI Review",
        "url": "https://linear.app/team-pulse/issue/DESIGN-42",
        "metadata": {"identifier": "DESIGN-42", "state": "In Progress", "demo_seed": True},
        "received_at": hours_ago(52),
    },
]


def main() -> None:
    supabase = get_supabase()
    # Clear prior demo rows first so reruns before each demo don't pile up
    # duplicate events / inflate counts / double the narrative.
    supabase.table("activity_events").delete().eq("metadata->>demo_seed", "true").execute()
    supabase.table("activity_events").insert(EVENTS).execute()
    print(f"Seeded {len(EVENTS)} demo events across github, linear, figma, notion (3 actors).")


if __name__ == "__main__":
    main()
