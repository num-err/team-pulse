"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Sparkles,
  RefreshCw,
  Send,
  CheckCircle2,
  AlertCircle,
  Users,
  Activity,
  Plus,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ActorAvatar } from "@/components/actor-avatar";

interface ActorDigest {
  actor: string;
  summary: string;
  event_count: number;
}

interface TeamDigest {
  date: string;
  actor_count: number;
  event_count: number;
  team_summary: string;
  actors: ActorDigest[];
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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

function apiHeaders(): HeadersInit {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

async function apiPost<T>(path: string): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  try {
    const res = await fetch(`${API_URL}${path}`, { method: "POST", headers: apiHeaders() });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail ?? `Error ${res.status}` };
    }
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return { ok: false, error: "Could not reach the API." };
  }
}

export default function DashboardPage() {
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [team, setTeam] = useState<TeamState>({ status: "idle" });
  const [teamSlack, setTeamSlack] = useState<SlackState>({ status: "idle" });

  const [manualInput, setManualInput] = useState("");
  const [manualOpen, setManualOpen] = useState(false);
  const [manualActors, setManualActors] = useState<string[]>([]);
  const [manualDigests, setManualDigests] = useState<Record<string, SoloState>>({});
  const [manualSlack, setManualSlack] = useState<Record<string, SlackState>>({});

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => setApiUp(r.ok))
      .catch(() => setApiUp(false));
  }, []);

  async function generateTeamDigest() {
    setTeam({ status: "loading" });
    setTeamSlack({ status: "idle" });
    const result = await apiPost<TeamDigest>("/digest/team");
    setTeam(result.ok ? { status: "done", data: result.data } : { status: "error", error: result.error });
  }

  async function sendTeamToSlack() {
    setTeamSlack({ status: "sending" });
    const result = await apiPost("/slack/deliver-team");
    setTeamSlack(result.ok ? { status: "sent" } : { status: "error", error: result.error });
  }

  async function addManualActor() {
    const actor = manualInput.trim();
    if (!actor) return;
    setManualInput("");
    if (!manualActors.includes(actor)) setManualActors((prev) => [...prev, actor]);
    setManualDigests((prev) => ({ ...prev, [actor]: { status: "loading" } }));
    const result = await apiPost<SoloDigest>(`/digest/generate?actor=${encodeURIComponent(actor)}`);
    setManualDigests((prev) => ({
      ...prev,
      [actor]: result.ok ? { status: "done", data: result.data } : { status: "error", error: result.error },
    }));
  }

  async function sendManualToSlack(actor: string) {
    setManualSlack((prev) => ({ ...prev, [actor]: { status: "sending" } }));
    const result = await apiPost(`/slack/deliver?actor=${encodeURIComponent(actor)}`);
    setManualSlack((prev) => ({
      ...prev,
      [actor]: result.ok ? { status: "sent" } : { status: "error", error: result.error },
    }));
  }

  const teamActorNames = team.status === "done" ? new Set(team.data.actors.map((a) => a.actor)) : new Set<string>();
  const visibleManualActors = manualActors.filter((a) => !teamActorNames.has(a));

  return (
    <main className="relative min-h-screen">
      <div className="bg-grid pointer-events-none fixed inset-0 [mask-image:radial-gradient(ellipse_70%_60%_at_50%_0%,black,transparent)]" />
      <div
        aria-hidden
        className="pointer-events-none fixed -top-40 left-1/2 h-[32rem] w-[32rem] -translate-x-1/2 rounded-full bg-violet-600/15 blur-[120px]"
      />

      <div className="relative z-10 mx-auto max-w-5xl px-6 py-10">
        <header className="mb-10 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Team <span className="gradient-text">Pulse</span>
            </h1>
            <p className="text-sm text-muted-foreground">
              Today&apos;s async standup, synthesized from what your team already shipped.
            </p>
          </div>
          <div className="glass flex items-center gap-2 rounded-full px-3 py-1.5 text-xs">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                apiUp === null ? "bg-muted-foreground" : apiUp ? "animate-pulse-dot bg-success" : "bg-destructive"
              }`}
            />
            <span className="text-muted-foreground">
              {apiUp === null ? "Checking API…" : apiUp ? "API connected" : "API unreachable"}
            </span>
          </div>
        </header>

        {/* Hero action */}
        <section className="glass glow-border relative mb-8 overflow-hidden rounded-2xl p-8 text-center">
          <div className="mx-auto flex max-w-md flex-col items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-sky-400">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold">Generate today&apos;s team digest</h2>
            <p className="text-sm text-muted-foreground">
              One click pulls the last 24h of GitHub, Linear, and Notion activity across
              the whole team and asks Claude to write the rollup.
            </p>
            <div className="flex items-center gap-2">
              <Button
                size="lg"
                onClick={generateTeamDigest}
                disabled={team.status === "loading"}
                className="bg-gradient-to-r from-violet-500 to-sky-400 text-white hover:opacity-90"
              >
                {team.status === "loading" ? (
                  <>
                    <RefreshCw className="mr-1.5 h-4 w-4 animate-spin" /> Synthesizing…
                  </>
                ) : team.status === "done" ? (
                  <>
                    <RefreshCw className="mr-1.5 h-4 w-4" /> Regenerate
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-1.5 h-4 w-4" /> Generate team digest
                  </>
                )}
              </Button>
            </div>
          </div>
        </section>

        <AnimatePresence mode="wait">
          {team.status === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="glass mb-8 flex flex-col items-center gap-3 rounded-2xl p-10 text-center"
            >
              <AlertCircle className="h-8 w-8 text-muted-foreground" />
              <p className="font-medium">{team.error}</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Team Pulse only looks at the last 24 hours. Push a commit, open a PR, or
                trigger a webhook, then try again.
              </p>
            </motion.div>
          )}

          {team.status === "done" && (
            <motion.div
              key="done"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              {/* Team summary card */}
              <section className="glass glow-border mb-8 rounded-2xl p-7">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold">Team digest — {team.data.date}</h3>
                    <div className="mt-2 flex gap-2">
                      <Badge variant="accent">
                        <Users className="h-3 w-3" /> {team.data.actor_count} teammate
                        {team.data.actor_count !== 1 ? "s" : ""}
                      </Badge>
                      <Badge>
                        <Activity className="h-3 w-3" /> {team.data.event_count} event
                        {team.data.event_count !== 1 ? "s" : ""}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={teamSlack.status === "sending" || teamSlack.status === "sent"}
                    onClick={sendTeamToSlack}
                  >
                    {teamSlack.status === "sent" ? (
                      <>
                        <CheckCircle2 className="mr-1.5 h-3.5 w-3.5 text-success" /> Sent to Slack
                      </>
                    ) : teamSlack.status === "sending" ? (
                      "Sending…"
                    ) : (
                      <>
                        <Send className="mr-1.5 h-3.5 w-3.5" /> Send to Slack
                      </>
                    )}
                  </Button>
                </div>
                <p className="leading-relaxed text-foreground/90">{team.data.team_summary}</p>
                {teamSlack.status === "error" && (
                  <p className="mt-2 text-xs text-destructive">{teamSlack.error}</p>
                )}
              </section>

              {/* Per-actor grid */}
              <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {team.data.actors.map((a, i) => (
                  <ActorCard
                    key={a.actor}
                    actor={a.actor}
                    summary={a.summary}
                    eventCount={a.event_count}
                    delay={i * 0.06}
                    slackState={manualSlack[a.actor]}
                    onSendSlack={() => sendManualToSlack(a.actor)}
                  />
                ))}
              </section>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Manual add */}
        <section className="mt-10">
          <button
            onClick={() => setManualOpen((v) => !v)}
            className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ChevronDown className={`h-4 w-4 transition-transform ${manualOpen ? "rotate-180" : ""}`} />
            Add a teammate manually
          </button>

          <AnimatePresence>
            {manualOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="mb-6 mt-4 flex gap-2">
                  <input
                    type="text"
                    placeholder="GitHub username or actor name"
                    value={manualInput}
                    onChange={(e) => setManualInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addManualActor()}
                    className="flex h-9 w-full max-w-xs rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                  <Button onClick={addManualActor} disabled={!manualInput.trim()}>
                    <Plus className="mr-1 h-3.5 w-3.5" /> Add
                  </Button>
                </div>

                {visibleManualActors.length > 0 && (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {visibleManualActors.map((actor) => {
                      const d = manualDigests[actor];
                      return (
                        <ActorCard
                          key={actor}
                          actor={actor}
                          summary={d?.status === "done" ? d.data.summary : undefined}
                          eventCount={d?.status === "done" ? d.data.event_count : undefined}
                          loading={d?.status === "loading"}
                          error={d?.status === "error" ? d.error : undefined}
                          slackState={manualSlack[actor]}
                          onSendSlack={() => sendManualToSlack(actor)}
                        />
                      );
                    })}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {team.status === "idle" && (
          <p className="mt-10 text-center text-xs text-muted-foreground">
            Nothing generated yet — click &quot;Generate team digest&quot; above to pull today&apos;s activity.
          </p>
        )}
      </div>
    </main>
  );
}

function ActorCard({
  actor,
  summary,
  eventCount,
  loading,
  error,
  delay = 0,
  slackState,
  onSendSlack,
}: {
  actor: string;
  summary?: string;
  eventCount?: number;
  loading?: boolean;
  error?: string;
  delay?: number;
  slackState?: SlackState;
  onSendSlack: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      whileHover={{ y: -3 }}
      className="glass flex flex-col gap-3 rounded-xl p-5 transition-shadow hover:shadow-[0_0_0_1px_hsl(var(--primary)/0.3),0_8px_24px_-8px_hsl(var(--primary)/0.4)]"
    >
      <div className="flex items-center gap-3">
        <ActorAvatar actor={actor} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{actor}</p>
          {eventCount !== undefined && (
            <p className="text-xs text-muted-foreground">
              {eventCount} event{eventCount !== 1 ? "s" : ""}
            </p>
          )}
        </div>
      </div>

      {loading && <p className="animate-pulse text-sm text-muted-foreground">Generating digest…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {summary && <p className="text-sm leading-relaxed text-foreground/90">{summary}</p>}

      {summary && (
        <div className="mt-1 flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={slackState?.status === "sending" || slackState?.status === "sent"}
            onClick={onSendSlack}
          >
            {slackState?.status === "sent" ? (
              <>
                <CheckCircle2 className="mr-1.5 h-3.5 w-3.5 text-success" /> Sent
              </>
            ) : slackState?.status === "sending" ? (
              "Sending…"
            ) : (
              <>
                <Send className="mr-1.5 h-3.5 w-3.5" /> Send to Slack
              </>
            )}
          </Button>
          {slackState?.status === "error" && (
            <span className="text-xs text-destructive">{slackState.error}</span>
          )}
        </div>
      )}
    </motion.div>
  );
}
