// Demo mode: a static, backend-free version of the dashboard for public showcase
// builds (e.g. GitHub Pages). Enabled at build time with NEXT_PUBLIC_DEMO_MODE=true.
// The data mirrors the 4-person cast in backend/scripts/seed_demo.py, with health
// evidence strings in the exact format backend/app/services/health.py produces.

export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

// The viewer's local calendar date (toISOString would give UTC, which is
// "tomorrow" for US evening visitors).
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

const ACTORS = [
  {
    actor: "Dev Okoye",
    summary:
      "Dev spent the day deep in the currency rounding bug on acme/pricing-service, pushing seven more commits — including a revert and a switch to Banker's rounding — several of which failed CI. The fix PR opened four days ago is still unmerged, and the Linear ticket hasn't moved since it was started. Plenty of effort, but no clear progress yet.",
    event_count: 8,
    sources: ["github", "linear"],
    health: {
      state: "THRASHING",
      evidence:
        "16 commit/edit events to acme/pricing-service over 3 days, 0 merges, 7 CI failures. One PR open 4d, unmerged.",
    },
  },
  {
    actor: "Marcus Webb",
    summary:
      "Marcus added retry logic to the payment webhook handler and fixed a flaky test in the checkout integration suite. He followed up by merging the webhook-retry PR and pushing the next step of the checkout migration to the new payment provider, building on yesterday's merged order-total refactor.",
    event_count: 4,
    sources: ["github"],
    health: {
      state: "HEALTHY",
      evidence: "6 events in the last 3 days, including a PR merged, a ticket moved to Done.",
    },
  },
  {
    actor: "Priya Sharma",
    summary:
      "Priya updated the Q3 Roadmap for Payments & Billing and published the enterprise customer interview synthesis in Notion. She also closed out the Q3 pricing tiers ticket in Linear, unblocking the self-serve upgrade work she scoped yesterday.",
    event_count: 3,
    sources: ["notion", "linear"],
    health: {
      state: "HEALTHY",
      evidence: "4 events in the last 3 days, including a ticket moved to Done.",
    },
  },
  {
    actor: "Sara Kim",
    summary:
      "Sara left spacing feedback on the empty-state illustration and updated the checkout button color to match brand guidelines in Figma. This follows her onboarding flow v4 being marked ready for handoff two days ago.",
    event_count: 2,
    sources: ["figma"],
    health: {
      state: "HEALTHY",
      evidence: "3 events in the last 3 days, including a milestone.",
    },
  },
] as const;

function teamDigest() {
  return {
    date: today(),
    actor_count: ACTORS.length,
    event_count: ACTORS.reduce((n, a) => n + a.event_count, 0),
    team_summary:
      "The payments push is moving: Marcus merged webhook retry logic and advanced the checkout provider migration, Priya closed out Q3 pricing tiers and shared the enterprise interview synthesis, and Sara's onboarding v4 is ready for engineering handoff. The one spot to watch is the currency rounding fix — Dev has been iterating on it for three days with repeated CI failures and no merge, so it may be worth pairing on before it holds up EU checkout.",
    actors: ACTORS,
    blockers: [],
    attention: ACTORS.filter((a) => a.health.state !== "HEALTHY").map((a) => ({
      actor: a.actor,
      state: a.health.state,
      evidence: a.health.evidence,
    })),
  };
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Stand-in for the real API: same response shapes, canned data, simulated latency. */
export async function demoPost(path: string): Promise<{ ok: true; data: unknown } | { ok: false; error: string }> {
  const url = new URL(path, "http://demo");
  switch (url.pathname) {
    case "/digest/team":
      await sleep(1600);
      return { ok: true, data: teamDigest() };
    case "/digest/generate": {
      await sleep(900);
      const name = (url.searchParams.get("actor") ?? "").trim().toLowerCase();
      const match = ACTORS.find((a) => a.actor.toLowerCase() === name);
      return match
        ? { ok: true, data: { ...match, date: today() } }
        : { ok: false, error: `No activity for ${url.searchParams.get("actor")} in the last 24 hours (demo data).` };
    }
    case "/slack/deliver":
    case "/slack/deliver-team":
      await sleep(700);
      return { ok: true, data: { delivered: true, demo: true } };
    default:
      return { ok: false, error: "Not available in demo mode." };
  }
}
