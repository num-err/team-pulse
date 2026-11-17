"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";
import { api, type Workspace } from "@/lib/api";
import { SessionProvider, useSession } from "@/lib/session";

export default function OnboardingPage() {
  return (
    <SessionProvider>
      <CreateWorkspace />
    </SessionProvider>
  );
}

function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

function allTimezones(current: string): string[] {
  const supported = (Intl as unknown as { supportedValuesOf?: (k: string) => string[] }).supportedValuesOf;
  const zones = supported ? supported("timeZone") : [];
  return Array.from(new Set(["UTC", current, ...zones]));
}

const fieldClass =
  "mt-1.5 h-9 w-full rounded-md border border-input bg-card px-3 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function CreateWorkspace() {
  const router = useRouter();
  const { state, refresh, selectWorkspace } = useSession();
  const detected = useMemo(browserTimezone, []);
  const zones = useMemo(() => allTimezones(detected), [detected]);

  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState(detected);
  const [time, setTime] = useState("09:00");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const created = await api<Workspace>("/workspaces", { method: "POST", body: { name: name.trim(), timezone } });
    if (!created.ok) {
      setSaving(false);
      setError(created.error);
      return;
    }
    const [hour, minute] = time.split(":").map(Number);
    if (hour !== 9 || minute !== 0) {
      await api(`/workspaces/${created.data.id}`, { method: "PATCH", body: { digest_hour: hour, digest_minute: minute } });
    }
    await refresh();
    selectWorkspace(created.data.id);
    router.replace("/dashboard");
  }

  const hasWorkspaces = state.status === "ready" && state.me.workspaces.length > 0;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
      <Link href="/" className="mb-8" aria-label="Team Pulse home">
        <Logo />
      </Link>

      <div className="w-full max-w-md rounded-xl border bg-card p-6 shadow-card sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-wider text-primary">Get started</p>
        <h1 className="mt-2 text-lg font-semibold">Create your team&apos;s workspace</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          A workspace holds one team&apos;s activity and digests. You can connect Slack and GitHub next.
        </p>

        {state.status === "loading" ? (
          <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
            <RefreshCw className="h-4 w-4 animate-spin" /> Loading your account…
          </p>
        ) : state.status === "error" ? (
          <p className="mt-6 text-sm text-red-600">{state.error}</p>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block">
              <span className="text-sm font-medium">Team name</span>
              <input
                required
                maxLength={80}
                placeholder="e.g. Payments Engineering"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={fieldClass}
              />
            </label>

            <div className="grid grid-cols-[1fr_auto] gap-3">
              <label className="block">
                <span className="text-sm font-medium">Timezone</span>
                <select value={timezone} onChange={(e) => setTimezone(e.target.value)} className={fieldClass}>
                  {zones.map((z) => (
                    <option key={z} value={z}>
                      {z.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-medium">Digest time</span>
                <input type="time" required value={time} onChange={(e) => setTime(e.target.value)} className={fieldClass} />
              </label>
            </div>
            <p className="text-xs text-muted-foreground">
              The daily digest posts to Slack at this time, in this timezone, every day there&apos;s activity.
            </p>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <div className="flex items-center justify-between gap-3 pt-2">
              {hasWorkspaces ? (
                <Button type="button" variant="ghost" onClick={() => router.push("/dashboard")}>
                  Cancel
                </Button>
              ) : (
                <span className="truncate text-xs text-muted-foreground">
                  {state.status === "ready" && state.me.user.email}
                </span>
              )}
              <Button type="submit" disabled={saving || !name.trim()}>
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}
                Create workspace <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </form>
        )}
      </div>
    </main>
  );
}
