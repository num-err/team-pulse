"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Github,
  LayoutDashboard,
  LogOut,
  Plug,
  Plus,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ActorAvatar } from "@/components/actor-avatar";
import { SourceIcons, SOURCE_META } from "@/components/source-icons";
import { HealthBadge, HEALTH_META, type Health, type HealthState } from "@/components/health-badge";
import { LogoMark } from "@/components/logo";
import { DEMO_MODE } from "@/lib/demo";
import { api, API_URL, ws, type Integration, type Workspace } from "@/lib/api";
import { SessionProvider, useSession } from "@/lib/session";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ types */

interface ActorDigest {
  actor: string;
  summary: string;
  event_count: number;
  sources: string[];
  health?: Health;
}

interface Blocker {
  title: string;
  repo: string;
  actor: string;
  hours_since_activity: number;
  url?: string;
}

interface AttentionItem {
  actor: string;
  state: HealthState;
  evidence: string;
}

interface TeamDigest {
  date: string;
  actor_count: number;
  event_count: number;
  team_summary: string;
  actors: ActorDigest[];
  blockers: Blocker[];
  attention: AttentionItem[];
}

interface SoloDigest extends ActorDigest {
  date: string;
}

type TeamState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "done"; data: TeamDigest };

type SlackState = { status: "idle" | "sending" | "sent" | "error"; error?: string };

type SoloState =
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "done"; data: SoloDigest };

/* -------------------------------------------------------------------- api */

const REPO_URL = "https://github.com/num-err/team-pulse";

const slug = (s: string) => `person-${s.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

function formatDate(iso: string) {
  const d = new Date(`${iso}T12:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}

/* ------------------------------------------------------------------- page */

export default function DashboardPage() {
  return (
    <SessionProvider>
      <DashboardGate />
    </SessionProvider>
  );
}

/** Waits for the session; sends signed-in users with no workspace to onboarding. */
function DashboardGate() {
  const router = useRouter();
  const { state } = useSession();
  const needsWorkspace = state.status === "ready" && !state.workspace;

  useEffect(() => {
    if (needsWorkspace) router.replace("/onboarding");
  }, [needsWorkspace, router]);

  if (state.status === "error") {
    return (
      <CenteredMessage title="Couldn't load your account" body={state.error}>
        <Button asChild variant="outline">
          <Link href="/login">Back to sign in</Link>
        </Button>
      </CenteredMessage>
    );
  }
  if (state.status !== "ready" || !state.workspace) {
    return (
      <CenteredMessage title="Loading your workspace…">
        <RefreshCw className="h-5 w-5 animate-spin text-muted-foreground" />
      </CenteredMessage>
    );
  }
  return <Dashboard key={state.workspace.id} workspace={state.workspace} />;
}

function CenteredMessage({ title, body, children }: { title: string; body?: string; children?: React.ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background px-4 text-center">
      <LogoMark className="h-9 w-9" />
      <h1 className="font-semibold">{title}</h1>
      {body && <p className="max-w-sm text-sm text-muted-foreground">{body}</p>}
      {children}
    </main>
  );
}

function Dashboard({ workspace }: { workspace: Workspace }) {
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [team, setTeam] = useState<TeamState>({ status: "idle" });
  const [teamSlack, setTeamSlack] = useState<SlackState>({ status: "idle" });
  const [personSlack, setPersonSlack] = useState<Record<string, SlackState>>({});
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [integrations, setIntegrations] = useState<Integration[] | null>(null);

  const [lookupInput, setLookupInput] = useState("");
  const [lookupActors, setLookupActors] = useState<string[]>([]);
  const [lookupDigests, setLookupDigests] = useState<Record<string, SoloState>>({});

  const path = (p: string) => ws(workspace.id, p);

  async function generateTeamDigest() {
    setTeam({ status: "loading" });
    setTeamSlack({ status: "idle" });
    setPersonSlack({});
    const result = await api<TeamDigest>(path("/digest/team"), { method: "POST" });
    if (result.ok) setLastUpdated(new Date());
    setTeam(result.ok ? { status: "done", data: result.data } : { status: "error", error: result.error });
  }

  useEffect(() => {
    if (DEMO_MODE) {
      // The public demo opens on a populated dashboard instead of an empty one.
      setApiUp(true);
      generateTeamDigest();
      return;
    }
    fetch(`${API_URL}/health`)
      .then((r) => setApiUp(r.ok))
      .catch(() => setApiUp(false));
    api<{ integrations: Integration[] }>(path("/integrations")).then((r) => r.ok && setIntegrations(r.data.integrations));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function sendTeamToSlack() {
    setTeamSlack({ status: "sending" });
    const result = await api(path("/slack/deliver-team"), { method: "POST" });
    setTeamSlack(result.ok ? { status: "sent" } : { status: "error", error: result.error });
  }

  async function sendPersonToSlack(actor: string) {
    setPersonSlack((prev) => ({ ...prev, [actor]: { status: "sending" } }));
    const result = await api(path(`/slack/deliver?actor=${encodeURIComponent(actor)}`), { method: "POST" });
    setPersonSlack((prev) => ({
      ...prev,
      [actor]: result.ok ? { status: "sent" } : { status: "error", error: result.error },
    }));
  }

  async function lookupActor() {
    const actor = lookupInput.trim();
    if (!actor) return;
    setLookupInput("");
    if (!lookupActors.includes(actor)) setLookupActors((prev) => [...prev, actor]);
    setLookupDigests((prev) => ({ ...prev, [actor]: { status: "loading" } }));
    const result = await api<SoloDigest>(path(`/digest/generate?actor=${encodeURIComponent(actor)}`), {
      method: "POST",
    });
    setLookupDigests((prev) => ({
      ...prev,
      [actor]: result.ok ? { status: "done", data: result.data } : { status: "error", error: result.error },
    }));
  }

  const data = team.status === "done" ? team.data : null;
  const attentionCount = data ? data.attention.length + data.blockers.length : 0;
  const sortedActors = data
    ? [...data.actors].sort(
        (a, b) => HEALTH_META[a.health?.state ?? "IDLE"].rank - HEALTH_META[b.health?.state ?? "IDLE"].rank
      )
    : [];

  return (
    <div className="min-h-screen bg-background">
      <Sidebar attentionCount={attentionCount} workspace={workspace} />

      <div className="lg:pl-60">
        {/* Top bar */}
        <header className="sticky top-0 z-20 border-b bg-card/90 backdrop-blur supports-[backdrop-filter]:bg-card/75">
          <div className="flex h-14 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <Link href="/" className="lg:hidden" aria-label="Team Pulse home">
                <LogoMark className="h-7 w-7" />
              </Link>
              <nav className="flex min-w-0 items-center gap-1.5 text-sm text-muted-foreground">
                <span className="hidden truncate sm:inline">{workspace.name}</span>
                <span className="hidden sm:inline">/</span>
                <span className="truncate font-medium text-foreground">Daily digest</span>
              </nav>
            </div>
            <ConnectionStatus apiUp={apiUp} />
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
          {/* Page header */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Daily digest</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {data ? formatDate(data.date) : "Today"} · Activity from the last 24 hours across GitHub, Linear,
                Notion and Figma.
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant="outline"
                onClick={sendTeamToSlack}
                disabled={!data || teamSlack.status === "sending" || teamSlack.status === "sent"}
              >
                {teamSlack.status === "sent" ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Sent to Slack
                  </>
                ) : teamSlack.status === "sending" ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" /> Sending…
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" /> Send to Slack
                  </>
                )}
              </Button>
              <Button onClick={generateTeamDigest} disabled={team.status === "loading"}>
                <RefreshCw className={cn("h-4 w-4", team.status === "loading" && "animate-spin")} />
                {team.status === "loading" ? "Generating…" : data ? "Regenerate" : "Generate digest"}
              </Button>
            </div>
          </div>
          {(lastUpdated || teamSlack.status === "error") && (
            <p className={cn("mt-2 text-xs", teamSlack.status === "error" ? "text-red-600" : "text-muted-foreground")}>
              {teamSlack.status === "error"
                ? teamSlack.error
                : `Generated at ${lastUpdated!.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}${
                    DEMO_MODE ? " · Sample data" : ""
                  }`}
            </p>
          )}

          <div className="mt-8 space-y-8">
            {team.status === "idle" && <EmptyState onGenerate={generateTeamDigest} />}
            {team.status === "loading" && <LoadingState />}
            {team.status === "error" && <ErrorState error={team.error} onRetry={generateTeamDigest} />}

            {data && (
              <>
                {/* KPIs */}
                <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <StatTile label="Contributors" value={data.actor_count} hint="Active in the last 24h" />
                  <StatTile label="Events" value={data.event_count} hint="Commits, PRs, tickets, docs" />
                  <StatTile
                    label="Needs attention"
                    value={data.attention.length}
                    hint={data.attention.length ? "Health signals flagged" : "No one flagged"}
                    tone={data.attention.length ? "warning" : undefined}
                  />
                  <StatTile
                    label="Stale tickets"
                    value={data.blockers.length}
                    hint="In Progress, idle 48h+"
                    tone={data.blockers.length ? "warning" : undefined}
                  />
                </section>

                {/* Attention */}
                <section id="attention" className="scroll-mt-20">
                  <SectionHeading
                    title="Needs attention"
                    description="People and tickets the health engine thinks are worth a check-in."
                    count={attentionCount}
                  />
                  {attentionCount === 0 ? (
                    <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3.5 text-sm text-muted-foreground shadow-xs">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      Nothing flagged — everyone with open work is making progress.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {data.attention.map((item) => (
                        <AttentionRow key={`${item.actor}-${item.state}`} item={item} />
                      ))}
                      {data.blockers.map((b) => (
                        <BlockerRow key={`${b.repo}-${b.title}`} blocker={b} />
                      ))}
                    </div>
                  )}
                </section>

                {/* Summary */}
                <section id="summary" className="scroll-mt-20">
                  <SectionHeading title="Team summary" />
                  <div className="rounded-lg border bg-card p-5 shadow-xs sm:p-6">
                    <div className="mb-3 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                      <Sparkles className="h-3.5 w-3.5 text-primary" />
                      AI-generated summary · Claude Haiku
                    </div>
                    <p className="text-[15px] leading-7 text-foreground/90">{data.team_summary}</p>
                  </div>
                </section>

                {/* Team */}
                <section id="team" className="scroll-mt-20">
                  <SectionHeading
                    title="Team"
                    description="Per-person standups, written from each person's own activity."
                    count={data.actors.length}
                  />
                  <ul className="divide-y overflow-hidden rounded-lg border bg-card shadow-xs">
                    {sortedActors.map((a) => (
                      <PersonRow
                        key={a.actor}
                        person={a}
                        slackState={personSlack[a.actor]}
                        onSendSlack={() => sendPersonToSlack(a.actor)}
                      />
                    ))}
                  </ul>
                </section>
              </>
            )}

            {/* Lookup */}
            <section id="lookup" className="scroll-mt-20">
              <SectionHeading
                title="Look up a teammate"
                description="Generate a standup for one person, even if they're not in today's digest."
              />
              <div className="rounded-lg border bg-card p-4 shadow-xs">
                <form
                  className="flex flex-col gap-2 sm:flex-row"
                  onSubmit={(e) => {
                    e.preventDefault();
                    lookupActor();
                  }}
                >
                  <div className="relative flex-1 sm:max-w-sm">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder={DEMO_MODE ? "Try “Marcus Webb”" : "GitHub username or display name"}
                      value={lookupInput}
                      onChange={(e) => setLookupInput(e.target.value)}
                      className="h-9 w-full rounded-md border border-input bg-card pl-9 pr-3 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                  </div>
                  <Button type="submit" variant="outline" disabled={!lookupInput.trim()}>
                    Look up
                  </Button>
                </form>
                {lookupActors.length > 0 && (
                  <ul className="mt-4 divide-y overflow-hidden rounded-md border">
                    {lookupActors.map((actor) => {
                      const d = lookupDigests[actor];
                      if (d?.status === "done") {
                        return (
                          <PersonRow
                            key={actor}
                            person={d.data}
                            slackState={personSlack[actor]}
                            onSendSlack={() => sendPersonToSlack(actor)}
                          />
                        );
                      }
                      return (
                        <li key={actor} className="flex items-center gap-3 px-5 py-4 text-sm">
                          <ActorAvatar actor={actor} />
                          <span className="font-medium">{actor}</span>
                          <span className={cn("text-muted-foreground", d?.status === "error" && "text-red-600")}>
                            {d?.status === "error" ? d.error : "Generating…"}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </section>

            {/* Integrations */}
            <section id="integrations" className="scroll-mt-20 pb-8">
              <SectionHeading title="Integrations" description="Where Team Pulse reads activity and delivers digests." />
              <IntegrationsTable live={DEMO_MODE ? null : integrations} />
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- layout bits */

const NAV: { href: string; label: string; icon: LucideIcon; countKey?: boolean }[] = [
  { href: "#summary", label: "Daily digest", icon: LayoutDashboard },
  { href: "#attention", label: "Needs attention", icon: AlertTriangle, countKey: true },
  { href: "#team", label: "Team", icon: Users },
  { href: "#lookup", label: "Look up", icon: Search },
  { href: "#integrations", label: "Integrations", icon: Plug },
];

function Sidebar({ attentionCount, workspace }: { attentionCount: number; workspace: Workspace }) {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r bg-card lg:flex">
      <div className="flex h-14 items-center border-b px-5">
        <Link href="/" className="inline-flex items-center gap-2 text-[15px] font-semibold tracking-tight">
          <LogoMark className="h-6 w-6" />
          Team Pulse
        </Link>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-4">
        <p className="px-2 pb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Workspace</p>
        {NAV.map(({ href, label, icon: Icon, countKey }, i) => (
          <a
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
              i === 0
                ? "bg-secondary font-medium text-foreground"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            <span className="flex-1">{label}</span>
            {countKey && attentionCount > 0 && (
              <span className="rounded-full bg-amber-100 px-1.5 text-[11px] font-semibold text-amber-800 tabular">
                {attentionCount}
              </span>
            )}
          </a>
        ))}
      </nav>

      <div className="space-y-3 border-t p-4">
        <a
          href={REPO_URL}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <Github className="h-4 w-4" /> Source on GitHub
        </a>
        <WorkspaceSwitcher workspace={workspace} />
      </div>
    </aside>
  );
}

function WorkspaceSwitcher({ workspace }: { workspace: Workspace }) {
  const { state, selectWorkspace, signOut } = useSession();
  const workspaces = state.status === "ready" ? state.me.workspaces : [workspace];
  const email = state.status === "ready" ? state.me.user.email : null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2.5 rounded-md border bg-background p-2">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-slate-900 text-xs font-semibold text-white">
          {workspace.name.trim().charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          {workspaces.length > 1 ? (
            <select
              aria-label="Switch workspace"
              value={workspace.id}
              onChange={(e) => selectWorkspace(e.target.value)}
              className="w-full truncate bg-transparent text-sm font-medium focus:outline-none"
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          ) : (
            <p className="truncate text-sm font-medium">{workspace.name}</p>
          )}
          <p className="truncate text-xs text-muted-foreground">
            {DEMO_MODE ? "Demo workspace" : `${workspace.role[0].toUpperCase()}${workspace.role.slice(1)}`}
          </p>
        </div>
      </div>
      {!DEMO_MODE && (
        <div className="flex items-center justify-between gap-2 px-1 text-xs text-muted-foreground">
          <span className="truncate" title={email ?? undefined}>
            {email}
          </span>
          <div className="flex shrink-0 items-center gap-1">
            <Link href="/onboarding" title="New workspace" className="rounded p-1 hover:bg-secondary hover:text-foreground">
              <Plus className="h-3.5 w-3.5" />
            </Link>
            <button onClick={signOut} title="Sign out" className="rounded p-1 hover:bg-secondary hover:text-foreground">
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ConnectionStatus({ apiUp }: { apiUp: boolean | null }) {
  if (DEMO_MODE) {
    return (
      <Badge variant="accent" className="shrink-0">
        Demo · sample data
      </Badge>
    );
  }
  const label = apiUp === null ? "Checking API…" : apiUp ? "API connected" : "API unreachable";
  return (
    <span className="inline-flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          apiUp === null ? "bg-slate-300" : apiUp ? "bg-emerald-500" : "bg-red-500"
        )}
      />
      {label}
    </span>
  );
}

function SectionHeading({ title, description, count }: { title: string; description?: string; count?: number }) {
  return (
    <div className="mb-3">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        {title}
        {count !== undefined && (
          <span className="rounded-full bg-secondary px-2 text-xs font-medium text-muted-foreground tabular">{count}</span>
        )}
      </h2>
      {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
    </div>
  );
}

function StatTile({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: number;
  hint: string;
  tone?: "warning";
}) {
  return (
    <div className="rounded-lg border bg-card p-4 shadow-xs">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={cn("mt-1.5 text-2xl font-semibold tabular", tone === "warning" && "text-amber-700")}>{value}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

/* ---------------------------------------------------------------- content */

function AttentionRow({ item }: { item: AttentionItem }) {
  const stuck = item.state === "SILENT_STUCK";
  const Icon = stuck ? AlertOctagon : AlertTriangle;
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-lg border border-l-4 bg-card p-4 shadow-xs sm:flex-row sm:items-start",
        stuck ? "border-l-red-500" : "border-l-amber-500"
      )}
    >
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-md",
          stuck ? "bg-red-50 text-red-600" : "bg-amber-50 text-amber-600"
        )}
      >
        <Icon className="h-[18px] w-[18px]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{item.actor}</p>
          <HealthBadge state={item.state} />
        </div>
        <p className="mt-1 text-sm text-foreground/80">
          {stuck ? "Has open work but has gone quiet — is this blocked?" : "Lots of effort, no landing — worth a pairing session?"}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">{item.evidence}</p>
      </div>
      <Button asChild variant="outline" size="sm" className="self-start">
        <a href={`#${slug(item.actor)}`}>
          View activity <ArrowRight className="h-3.5 w-3.5" />
        </a>
      </Button>
    </div>
  );
}

function BlockerRow({ blocker }: { blocker: Blocker }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-l-4 border-l-amber-500 bg-card p-4 shadow-xs sm:flex-row sm:items-start">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-amber-50 text-amber-600">
        <AlertTriangle className="h-[18px] w-[18px]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{blocker.title}</p>
          <Badge variant="warning">Possibly blocked</Badge>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          In Progress with no activity for {blocker.hours_since_activity} hours · {blocker.actor} · {blocker.repo}
        </p>
      </div>
      {blocker.url && (
        <Button asChild variant="outline" size="sm" className="self-start">
          <a href={blocker.url} target="_blank" rel="noreferrer">
            Open ticket <ArrowRight className="h-3.5 w-3.5" />
          </a>
        </Button>
      )}
    </div>
  );
}

function PersonRow({
  person,
  slackState,
  onSendSlack,
}: {
  person: ActorDigest;
  slackState?: SlackState;
  onSendSlack: () => void;
}) {
  return (
    <li id={slug(person.actor)} className="scroll-mt-20 px-5 py-5">
      <div className="grid gap-4 md:grid-cols-[200px_1fr_auto] md:gap-6">
        <div className="flex items-start gap-3">
          <ActorAvatar actor={person.actor} />
          <div className="min-w-0">
            <p className="truncate font-medium">{person.actor}</p>
            {person.health && <HealthBadge state={person.health.state} className="mt-1" />}
          </div>
        </div>

        <div className="min-w-0">
          <p className="text-sm leading-6 text-foreground/85">{person.summary}</p>
          {person.health && (
            <p className="mt-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground/70">Signal:</span> {person.health.evidence}
            </p>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 md:flex-col md:items-end md:justify-start">
          <div className="flex items-center gap-2.5">
            <span className="text-xs text-muted-foreground tabular">
              {person.event_count} event{person.event_count !== 1 ? "s" : ""}
            </span>
            <SourceIcons sources={person.sources} />
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onSendSlack}
            disabled={slackState?.status === "sending" || slackState?.status === "sent"}
            className="-mr-2"
          >
            {slackState?.status === "sent" ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> Sent
              </>
            ) : slackState?.status === "sending" ? (
              "Sending…"
            ) : (
              <>
                <Send className="h-3.5 w-3.5" /> Send to Slack
              </>
            )}
          </Button>
          {slackState?.status === "error" && <span className="text-xs text-red-600">{slackState.error}</span>}
        </div>
      </div>
    </li>
  );
}

const INTEGRATIONS: { key: string; method: string; detail: string; connected: boolean }[] = [
  { key: "github", method: "Webhook · HMAC-SHA256", detail: "Pull requests and pushes", connected: true },
  { key: "linear", method: "Webhook · HMAC-SHA256", detail: "Issues and comments", connected: true },
  { key: "notion", method: "API polling", detail: "Page edits, synced before each digest", connected: true },
  { key: "figma", method: "Webhook · passcode", detail: "Comments and version saves", connected: false },
  { key: "slack", method: "Bot · chat:write", detail: "Daily digest at 09:00 UTC", connected: true },
];

/** `live` is the workspace's real connection status (null = show the demo's static view). */
function IntegrationsTable({ live }: { live: Integration[] | null }) {
  const connectedNow = (key: string, fallback: boolean) =>
    live ? Boolean(live.find((i) => i.provider === key)?.connected) : fallback;
  return (
    <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
      <table className="w-full text-sm">
        <thead className="border-b bg-secondary/60 text-left text-xs text-muted-foreground">
          <tr>
            <th className="px-5 py-2.5 font-medium">Source</th>
            <th className="hidden px-5 py-2.5 font-medium sm:table-cell">Method</th>
            <th className="hidden px-5 py-2.5 font-medium md:table-cell">What it reads</th>
            <th className="px-5 py-2.5 text-right font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {INTEGRATIONS.map(({ key, method, detail, connected }) => {
            const { icon: Icon, label } = SOURCE_META[key];
            return (
              <tr key={key}>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-2.5 font-medium">
                    <span className="flex h-7 w-7 items-center justify-center rounded-md border bg-background">
                      <Icon className="h-4 w-4" />
                    </span>
                    {label}
                  </span>
                </td>
                <td className="hidden px-5 py-3 text-muted-foreground sm:table-cell">{method}</td>
                <td className="hidden px-5 py-3 text-muted-foreground md:table-cell">{detail}</td>
                <td className="px-5 py-3 text-right">
                  {connectedNow(key, connected) ? (
                    <Badge variant="success">Connected</Badge>
                  ) : live && key !== "figma" ? (
                    <Badge variant="outline">Not connected</Badge>
                  ) : (
                    <Badge variant="outline">Requires paid plan</Badge>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ----------------------------------------------------------------- states */

function EmptyState({ onGenerate }: { onGenerate: () => void }) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed bg-card px-6 py-14 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-accent text-primary">
        <Sparkles className="h-5 w-5" />
      </div>
      <h3 className="mt-4 font-semibold">No digest yet today</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        Generate a digest to summarize the last 24 hours of team activity and flag anyone who looks stuck.
      </p>
      <Button className="mt-5" onClick={onGenerate}>
        <Sparkles className="h-4 w-4" /> Generate digest
      </Button>
    </div>
  );
}

function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  const quiet = error.toLowerCase().includes("no activity");
  return (
    <div className="flex flex-col items-center rounded-lg border bg-card px-6 py-12 text-center shadow-xs">
      <div
        className={cn(
          "flex h-11 w-11 items-center justify-center rounded-full",
          quiet ? "bg-secondary text-muted-foreground" : "bg-red-50 text-red-600"
        )}
      >
        {quiet ? <CheckCircle2 className="h-5 w-5" /> : <AlertOctagon className="h-5 w-5" />}
      </div>
      <h3 className="mt-4 font-semibold">{quiet ? "All quiet in the last 24 hours" : "Couldn't generate the digest"}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        {quiet
          ? "No team activity was recorded in the window. Push a commit, open a PR, or update a ticket, then try again."
          : `${error} Check that the API is running, then try again.`}
      </p>
      <Button variant="outline" className="mt-5" onClick={onRetry}>
        <RefreshCw className="h-4 w-4" /> Try again
      </Button>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-8" aria-busy aria-label="Generating digest">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-[98px] animate-pulse rounded-lg border bg-card p-4">
            <div className="h-3 w-20 rounded bg-secondary" />
            <div className="mt-3 h-6 w-10 rounded bg-secondary" />
          </div>
        ))}
      </div>
      <div className="animate-pulse rounded-lg border bg-card p-6">
        <div className="h-3 w-40 rounded bg-secondary" />
        <div className="mt-4 space-y-2.5">
          <div className="h-3 rounded bg-secondary" />
          <div className="h-3 rounded bg-secondary" />
          <div className="h-3 w-2/3 rounded bg-secondary" />
        </div>
      </div>
      <div className="divide-y rounded-lg border bg-card">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex animate-pulse gap-4 px-5 py-5">
            <div className="h-9 w-9 rounded-full bg-secondary" />
            <div className="flex-1 space-y-2.5">
              <div className="h-3 w-32 rounded bg-secondary" />
              <div className="h-3 rounded bg-secondary" />
            </div>
          </div>
        ))}
      </div>
      <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
        <RefreshCw className="h-4 w-4 animate-spin" /> Reading activity and writing summaries…
      </p>
    </div>
  );
}
