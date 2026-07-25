"""Seed a two-week, four-person activity_events cast for the health-engine demo.

Distinct from scripts/seed_demo_events.py (the older num-err/Ada Chen blocker
demo) — this script tags its rows with metadata.demo_cast = "health_v1" and
only wipes/reseeds rows with that tag, so the two seed scripts don't collide
if both are used against the same Supabase project.

Cast (names are consistent across every source, per-actor):
  Sara Kim      — designer, Figma only               -> HEALTHY
  Priya Sharma  — PM, Notion + Linear                 -> HEALTHY
  Marcus Webb   — engineer, GitHub + Linear            -> HEALTHY
  Dev Okoye     — engineer, stuck on a rounding bug    -> THRASHING

All timestamps are relative to now, so the demo looks current no matter when
this is run.

Usage:
    cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo.py
"""

from datetime import datetime, timedelta, timezone

from app.integrations.supabase_client import get_supabase

now = datetime.now(timezone.utc)

DEMO_CAST_TAG = "health_v1"


def hours_ago(h: float) -> str:
    return (now - timedelta(hours=h)).isoformat()


def _meta(**extra) -> dict:
    return {"demo_seed": True, "demo_cast": DEMO_CAST_TAG, **extra}


EVENTS: list[dict] = []

# ---------------------------------------------------------------------------
# Sara Kim — designer. Figma edits + comments, plus a "ready for handoff"
# milestone 2 days ago. Recent activity keeps her inside the 24h digest
# window; the milestone (tagged metadata.milestone) reads as forward motion
# inside the 72h health window. -> HEALTHY
# ---------------------------------------------------------------------------
EVENTS += [
    {
        "source": "figma",
        "event_type": "file_comment",
        "actor": "Sara Kim",
        "repo": "Onboarding Flow",
        "title": "Left feedback on empty-state illustration spacing",
        "url": "https://www.figma.com/file/demo-onboarding",
        "metadata": _meta(),
        "received_at": hours_ago(5),
    },
    {
        "source": "figma",
        "event_type": "file_comment",
        "actor": "Sara Kim",
        "repo": "Onboarding Flow",
        "title": "Swapped the checkout button color to match brand guidelines",
        "url": "https://www.figma.com/file/demo-onboarding",
        "metadata": _meta(),
        "received_at": hours_ago(20),
    },
    {
        "source": "figma",
        "event_type": "version_saved",
        "actor": "Sara Kim",
        "repo": "Onboarding Flow",
        "title": "Onboarding flow v4 — ready for handoff",
        "url": "https://www.figma.com/file/demo-onboarding",
        "metadata": _meta(milestone="ready_for_handoff"),
        "received_at": hours_ago(48),
    },
    # two-week texture
    {
        "source": "figma",
        "event_type": "file_comment",
        "actor": "Sara Kim",
        "repo": "Onboarding Flow",
        "title": "Explored three variants for the empty-state illustration",
        "url": "https://www.figma.com/file/demo-onboarding",
        "metadata": _meta(),
        "received_at": hours_ago(24 * 8),
    },
    {
        "source": "figma",
        "event_type": "version_saved",
        "actor": "Sara Kim",
        "repo": "Payment UI",
        "title": "Payment UI v2 — first pass",
        "url": "https://www.figma.com/file/demo-payment-ui",
        "metadata": _meta(),
        "received_at": hours_ago(24 * 11),
    },
]

# ---------------------------------------------------------------------------
# Priya Sharma — PM. Notion roadmap/synthesis edits, a ticket created, and a
# ticket moved to Done yesterday (real completion event). -> HEALTHY
# ---------------------------------------------------------------------------
EVENTS += [
    {
        "source": "notion",
        "event_type": "page_edited",
        "actor": "Priya Sharma",
        "repo": "notion",
        "title": "Q3 Roadmap — Payments & Billing",
        "url": "https://notion.so/demo-q3-roadmap",
        "metadata": _meta(),
        "received_at": hours_ago(3),
    },
    {
        "source": "notion",
        "event_type": "page_edited",
        "actor": "Priya Sharma",
        "repo": "notion",
        "title": "Customer Interview Synthesis — Enterprise Segment",
        "url": "https://notion.so/demo-interview-synthesis",
        "metadata": _meta(),
        "received_at": hours_ago(18),
    },
    {
        "source": "linear",
        "event_type": "issue_created",
        "actor": "Priya Sharma",
        "repo": "PM",
        "title": "Add self-serve upgrade flow",
        "url": "https://linear.app/team-pulse/issue/PM-58",
        "metadata": _meta(identifier="PM-58"),
        "received_at": hours_ago(30),
    },
    {
        "source": "linear",
        "event_type": "issue_completed",
        "actor": "Priya Sharma",
        "repo": "PM",
        "title": "Finalize Q3 pricing tiers doc",
        "url": "https://linear.app/team-pulse/issue/PM-51",
        "metadata": _meta(identifier="PM-51"),
        "received_at": hours_ago(20),
    },
    # two-week texture
    {
        "source": "notion",
        "event_type": "page_edited",
        "actor": "Priya Sharma",
        "repo": "notion",
        "title": "Competitive Landscape — Async Standup Tools",
        "url": "https://notion.so/demo-competitive-landscape",
        "metadata": _meta(),
        "received_at": hours_ago(24 * 6),
    },
    {
        "source": "linear",
        "event_type": "issue_created",
        "actor": "Priya Sharma",
        "repo": "PM",
        "title": "Finalize Q3 pricing tiers doc",
        "url": "https://linear.app/team-pulse/issue/PM-51",
        "metadata": _meta(identifier="PM-51"),
        "received_at": hours_ago(24 * 9),
    },
]

# ---------------------------------------------------------------------------
# Marcus Webb — engineer. Steady commits, two merges inside the 72h window,
# a Linear ticket closing. -> HEALTHY
# ---------------------------------------------------------------------------
EVENTS += [
    {
        "source": "github",
        "event_type": "commit_pushed",
        "actor": "Marcus Webb",
        "repo": "acme/checkout-service",
        "title": "Add retry logic to payment webhook handler",
        "url": "https://github.com/acme/checkout-service/commit/demo-mw1",
        "metadata": _meta(),
        "received_at": hours_ago(14),
    },
    {
        "source": "github",
        "event_type": "commit_pushed",
        "actor": "Marcus Webb",
        "repo": "acme/checkout-service",
        "title": "Fix flaky test in checkout integration suite",
        "url": "https://github.com/acme/checkout-service/commit/demo-mw2",
        "metadata": _meta(),
        "received_at": hours_ago(12),
    },
    {
        "source": "github",
        "event_type": "pr_merged",
        "actor": "Marcus Webb",
        "repo": "acme/checkout-service",
        "title": "Add retry logic for failed payment webhooks",
        "url": "https://github.com/acme/checkout-service/pull/204",
        "metadata": _meta(),
        "received_at": hours_ago(10),
    },
    {
        "source": "linear",
        "event_type": "issue_completed",
        "actor": "Marcus Webb",
        "repo": "ENG",
        "title": "Migrate checkout to new payment provider",
        "url": "https://linear.app/team-pulse/issue/ENG-210",
        "metadata": _meta(identifier="ENG-210"),
        "received_at": hours_ago(9),
    },
    {
        "source": "github",
        "event_type": "commit_pushed",
        "actor": "Marcus Webb",
        "repo": "acme/checkout-service",
        "title": "Refactor order total calculation module",
        "url": "https://github.com/acme/checkout-service/commit/demo-mw3",
        "metadata": _meta(),
        "received_at": hours_ago(52),
    },
    {
        "source": "github",
        "event_type": "pr_merged",
        "actor": "Marcus Webb",
        "repo": "acme/checkout-service",
        "title": "Refactor order total calculation",
        "url": "https://github.com/acme/checkout-service/pull/198",
        "metadata": _meta(),
        "received_at": hours_ago(50),
    },
    # two-week texture
    {
        "source": "github",
        "event_type": "commit_pushed",
        "actor": "Marcus Webb",
        "repo": "acme/checkout-service",
        "title": "Add integration test for webhook retries",
        "url": "https://github.com/acme/checkout-service/commit/demo-mw4",
        "metadata": _meta(),
        "received_at": hours_ago(24 * 7),
    },
    {
        "source": "linear",
        "event_type": "issue_started",
        "actor": "Marcus Webb",
        "repo": "ENG",
        "title": "Migrate checkout to new payment provider",
        "url": "https://linear.app/team-pulse/issue/ENG-210",
        "metadata": _meta(identifier="ENG-210"),
        "received_at": hours_ago(24 * 8),
    },
]

# ---------------------------------------------------------------------------
# Dev Okoye — engineer. Healthy first week (one merge, now well outside the
# 72h window), then three days of thrashing on a currency rounding bug: 16
# commits to the same repo, several failing CI, one PR opened days ago and
# never merged, and a Linear ticket left "In Progress". -> THRASHING
# ---------------------------------------------------------------------------
EVENTS += [
    # "healthy first week" flavor — outside every scoring window, pure texture
    {
        "source": "github",
        "event_type": "pr_merged",
        "actor": "Dev Okoye",
        "repo": "acme/pricing-service",
        "title": "Add currency conversion for EU checkout",
        "url": "https://github.com/acme/pricing-service/pull/301",
        "metadata": _meta(),
        "received_at": hours_ago(24 * 9),
    },
    {
        "source": "linear",
        "event_type": "issue_completed",
        "actor": "Dev Okoye",
        "repo": "ENG",
        "title": "Add currency conversion for EU checkout",
        "url": "https://linear.app/team-pulse/issue/ENG-188",
        "metadata": _meta(identifier="ENG-188"),
        "received_at": hours_ago(24 * 9 - 1),
    },
    # the stuck ticket — started 40h ago, never moved
    {
        "source": "linear",
        "event_type": "issue_started",
        "actor": "Dev Okoye",
        "repo": "ENG",
        "title": "Fix currency rounding bug",
        "url": "https://linear.app/team-pulse/issue/ENG-233",
        "metadata": _meta(identifier="ENG-233"),
        "received_at": hours_ago(40),
    },
    # the unmerged PR — opened 4 days ago
    {
        "source": "github",
        "event_type": "pr_opened",
        "actor": "Dev Okoye",
        "repo": "acme/pricing-service",
        "title": "WIP: fix rounding bug",
        "url": "https://github.com/acme/pricing-service/pull/312",
        "metadata": _meta(),
        "received_at": hours_ago(96),
    },
]

_DEV_COMMITS = [
    ("attempt 2 — round half up instead of truncating", False, 68),
    ("revert — broke the positive-amount case", True, 64),
    ("try a different rounding approach entirely", False, 60),
    ("attempt 3 — use Decimal instead of float", True, 56),
    ("debug: log intermediate rounding values", False, 52),
    ("attempt 4 — handle negative amounts", True, 48),
    ("still failing on negative amounts", False, 44),
    ("try Banker's rounding", True, 40),
    ("fix broken test fixture", False, 36),
    ("attempt 5 — special-case negative amounts", True, 32),
    ("revert — broke the positive case again", False, 28),
    ("add regression test for rounding", False, 24),
    ("attempt 6 — rewrite rounding helper from scratch", True, 18),
    ("narrow down the failing case", False, 12),
    ("attempt 7 — round at the cents boundary only", True, 6),
    ("still chasing the off-by-one-cent bug", False, 1.5),
]

for i, (message, failed, hours) in enumerate(_DEV_COMMITS):
    EVENTS.append({
        "source": "github",
        "event_type": "commit_pushed",
        "actor": "Dev Okoye",
        "repo": "acme/pricing-service",
        "title": message,
        "url": f"https://github.com/acme/pricing-service/commit/demo-dev{i}",
        "metadata": _meta(ci_status="failed") if failed else _meta(),
        "received_at": hours_ago(hours),
    })


def main() -> None:
    supabase = get_supabase()
    # Wipe only this script's rows (metadata.demo_cast), so the older
    # seed_demo_events.py demo cast (if present) is left untouched.
    supabase.table("activity_events").delete().eq("metadata->>demo_cast", DEMO_CAST_TAG).execute()
    supabase.table("activity_events").insert(EVENTS).execute()
    print(f"Seeded {len(EVENTS)} demo events for Sara Kim, Priya Sharma, Marcus Webb, Dev Okoye.")


if __name__ == "__main__":
    main()
