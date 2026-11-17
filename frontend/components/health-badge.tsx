import { cn } from "@/lib/utils";

export type HealthState = "HEALTHY" | "THRASHING" | "SILENT_STUCK" | "IDLE";

export interface Health {
  state: HealthState;
  evidence: string;
}

export const HEALTH_META: Record<
  HealthState,
  { label: string; pill: string; dot: string; description: string; rank: number }
> = {
  SILENT_STUCK: {
    label: "Silent & stuck",
    pill: "bg-red-50 text-red-700 ring-red-600/20",
    dot: "bg-red-500",
    description: "A ticket is In Progress, but there has been no activity of any kind for 48+ hours.",
    rank: 0,
  },
  THRASHING: {
    label: "Thrashing",
    pill: "bg-amber-50 text-amber-800 ring-amber-600/25",
    dot: "bg-amber-500",
    description:
      "Heavy churn on one repo or ticket — 8+ events in 3 days with no merge, plus a struggle signal such as failing CI.",
    rank: 1,
  },
  HEALTHY: {
    label: "Healthy",
    pill: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    dot: "bg-emerald-500",
    description: "Shipping. Recent activity includes a merged PR, a closed ticket, or a design milestone.",
    rank: 2,
  },
  IDLE: {
    label: "Idle",
    pill: "bg-slate-50 text-slate-600 ring-slate-500/20",
    dot: "bg-slate-400",
    description: "No recent activity and nothing open. Not a problem — just quiet.",
    rank: 3,
  },
};

/** Compact status pill with a colored dot — the one place health color appears. */
export function HealthBadge({ state, className }: { state: HealthState; className?: string }) {
  const meta = HEALTH_META[state];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        meta.pill,
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </span>
  );
}
