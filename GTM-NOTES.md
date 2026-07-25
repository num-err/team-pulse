# Team Pulse — Going-to-Market Notes

Untracked scratch doc (like `PITCH.md`) capturing a strategy conversation from
2026-07-01 about what to do *after* the pitch — how to get from "working demo"
to "real teams using this."

---

## The starting question

The pitch (`PITCH.md`) is written entirely around software teams — GitHub,
Linear, Notion. That's accurate to what's built, but it raised a bigger
question: companies have *many* teams (sales, support, marketing, HR), each
with their own tools. Should Team Pulse expand to cover all of them? And
separately — there's no signup flow at all right now (single-tenant, one
hardcoded Supabase project/Slack workspace/GitHub repo) — so how would teams
even start using this, how big should the tool get, and how do you get users
in the first place?

## Goal established

Confirmed goal: **get real teams/users using Team Pulse**, not just use it as
a portfolio/demo piece. That goal drives everything below.

## Recommended sequence (in order)

1. **Don't generalize yet — narrow and validate first.**
   The current pitch (eng teams drowning in standups) is specific and the
   demo already works end-to-end. Broadening to "every team in a company"
   means building integrations for tools with no feedback loop yet
   (Salesforce, Zendesk, HR systems) — a lot of engineering spent before
   confirming anyone wants even the current version.

2. **Get 2-3 pilot teams manually — concierge onboarding, not self-serve.**
   There's no signup today; it's single-tenant, hardcoded to one Supabase
   project / Slack workspace / GitHub repo (see the Auth section of
   `CLAUDE.md`). The fastest real path isn't building multi-tenancy first —
   it's standing up a dedicated instance per pilot team (same code, separate
   `.env` / Supabase project / Slack app each). Standard early-B2B practice:
   prove daily usage before investing in self-serve infra.

3. **Only build multi-tenancy once pilots show real pull.**
   If 2-3 teams are actually reading their digests daily after a few weeks,
   that's the signal to invest in OAuth connect flows, org accounts, and
   per-org data isolation in Supabase — not before.

4. **"Every team" comes after that, as an expansion — not a rewrite.**
   Once the eng-team version has traction, pick one adjacent team type
   (e.g. support via Zendesk) and validate it the same manual way, rather
   than building several new integrations speculatively.

## Main tradeoff

This path is slower and less impressive-sounding upfront than announcing a
"multi-tenant platform for every team in the company" — but it means every
hour of engineering work is backed by a real user who asked for it, instead
of speculative breadth.

## Open threads to pick up next time

- Who could realistically be the first 1-2 pilot teams (own workplace? a
  friend's startup? someone from network?)
- What "concierge onboarding" actually takes technically — fastest way to
  stand up a second isolated instance for a pilot (separate Supabase
  project + Slack app + `.env`, reusing the same codebase)
- Revisit the "every team" integration list (sales/support/marketing tools)
  once there's a validated eng-team pilot to point to
