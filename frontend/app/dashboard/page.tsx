"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface Digest {
  actor: string;
  summary: string;
  date: string;
  event_count: number;
}

interface DigestState {
  status: "loading" | "done" | "error";
  data?: Digest;
  error?: string;
}

interface SlackState {
  status: "idle" | "sending" | "sent" | "error";
  error?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

function apiHeaders(): HeadersInit {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

async function fetchDigest(actor: string): Promise<DigestState> {
  try {
    const res = await fetch(
      `${API_URL}/digest/generate?actor=${encodeURIComponent(actor)}`,
      { method: "POST", headers: apiHeaders() }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { status: "error", error: body.detail ?? `Error ${res.status}` };
    }
    const data: Digest = await res.json();
    return { status: "done", data };
  } catch {
    return { status: "error", error: "Could not reach the API." };
  }
}

async function sendToSlack(actor: string): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch(
      `${API_URL}/slack/deliver?actor=${encodeURIComponent(actor)}`,
      { method: "POST", headers: apiHeaders() }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail ?? `Error ${res.status}` };
    }
    return { ok: true };
  } catch {
    return { ok: false, error: "Could not reach the API." };
  }
}

export default function DashboardPage() {
  const [input, setInput] = useState("");
  const [actors, setActors] = useState<string[]>([]);
  const [digests, setDigests] = useState<Record<string, DigestState>>({});
  const [slack, setSlack] = useState<Record<string, SlackState>>({});

  async function addActor() {
    const actor = input.trim();
    if (!actor || actors.includes(actor)) return;
    setInput("");
    setActors((prev) => [...prev, actor]);
    setDigests((prev) => ({ ...prev, [actor]: { status: "loading" } }));
    const result = await fetchDigest(actor);
    setDigests((prev) => ({ ...prev, [actor]: result }));
  }

  async function refreshAll() {
    const updates: Record<string, DigestState> = {};
    actors.forEach((a) => (updates[a] = { status: "loading" }));
    setDigests((prev) => ({ ...prev, ...updates }));
    setSlack({});
    await Promise.all(
      actors.map(async (a) => {
        const result = await fetchDigest(a);
        setDigests((prev) => ({ ...prev, [a]: result }));
      })
    );
  }

  async function deliverToSlack(actor: string) {
    setSlack((prev) => ({ ...prev, [actor]: { status: "sending" } }));
    const result = await sendToSlack(actor);
    setSlack((prev) => ({
      ...prev,
      [actor]: result.ok
        ? { status: "sent" }
        : { status: "error", error: result.error },
    }));
  }

  return (
    <main className="container mx-auto max-w-5xl py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Team Pulse</h1>
        <p className="text-muted-foreground">
          Today&apos;s async standup — generated from your team&apos;s GitHub
          activity.
        </p>
      </header>

      <div className="mb-8 flex gap-2">
        <input
          type="text"
          placeholder="GitHub username"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addActor()}
          className="flex h-9 w-full max-w-xs rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <Button onClick={addActor} disabled={!input.trim()}>
          Generate
        </Button>
        {actors.length > 1 && (
          <Button variant="outline" onClick={refreshAll}>
            Refresh all
          </Button>
        )}
      </div>

      {actors.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          Enter a GitHub username above to generate a standup digest.
        </div>
      ) : (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {actors.map((actor) => {
            const digestState = digests[actor];
            const slackState = slack[actor];
            const isDone = digestState?.status === "done";

            return (
              <Card key={actor}>
                <CardHeader>
                  <CardTitle className="text-lg">{actor}</CardTitle>
                  <CardDescription>
                    {isDone && digestState.data
                      ? `${digestState.data.event_count} event${digestState.data.event_count !== 1 ? "s" : ""} · ${digestState.data.date}`
                      : "GitHub"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {digestState?.status === "loading" && (
                    <p className="animate-pulse text-sm text-muted-foreground">
                      Generating digest…
                    </p>
                  )}
                  {digestState?.status === "error" && (
                    <p className="text-sm text-destructive">{digestState.error}</p>
                  )}
                  {isDone && (
                    <>
                      <p className="text-sm leading-relaxed">
                        {digestState.data?.summary}
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={slackState?.status === "sending" || slackState?.status === "sent"}
                          onClick={() => deliverToSlack(actor)}
                        >
                          {slackState?.status === "sending"
                            ? "Sending…"
                            : slackState?.status === "sent"
                            ? "Sent to Slack"
                            : "Send to Slack"}
                        </Button>
                        {slackState?.status === "error" && (
                          <span className="text-xs text-destructive">
                            {slackState.error}
                          </span>
                        )}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </section>
      )}
    </main>
  );
}
