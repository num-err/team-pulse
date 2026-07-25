import { CheckCircle2, Repeat, AlertOctagon, Moon, type LucideIcon } from "lucide-react";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type HealthState = "HEALTHY" | "THRASHING" | "SILENT_STUCK" | "IDLE";

export interface Health {
  state: HealthState;
  evidence: string;
}

const HEALTH_META: Record<HealthState, { label: string; variant: BadgeProps["variant"]; icon: LucideIcon }> = {
  HEALTHY: { label: "Healthy", variant: "success", icon: CheckCircle2 },
  THRASHING: { label: "Thrashing", variant: "warning", icon: Repeat },
  SILENT_STUCK: { label: "Silent & stuck", variant: "destructive", icon: AlertOctagon },
  IDLE: { label: "Idle", variant: "outline", icon: Moon },
};

export function HealthBadge({ state, className }: { state: HealthState; className?: string }) {
  const meta = HEALTH_META[state];
  const Icon = meta.icon;
  return (
    <Badge variant={meta.variant} className={className}>
      <Icon className="h-3 w-3" /> {meta.label}
    </Badge>
  );
}

// Same four states, tuned for "hero" prominence rather than a compact pill:
// bigger icon chip + bold colored label. Only THRASHING/SILENT_STUCK pulse —
// those are the states worth an eye landing on faster; HEALTHY/IDLE stay calm
// on purpose (an idle actor isn't a problem, see Person Health Engine notes).
const HEALTH_HERO_META: Record<
  HealthState,
  { label: string; icon: LucideIcon; iconColor: string; iconBg: string; textColor: string; barColor: string; pulse: boolean }
> = {
  HEALTHY: {
    label: "Healthy",
    icon: CheckCircle2,
    iconColor: "text-success",
    iconBg: "bg-success/15",
    textColor: "text-success",
    barColor: "bg-success",
    pulse: false,
  },
  THRASHING: {
    label: "Thrashing",
    icon: Repeat,
    iconColor: "text-amber-300",
    iconBg: "bg-amber-400/15",
    textColor: "text-amber-300",
    barColor: "bg-amber-400",
    pulse: true,
  },
  SILENT_STUCK: {
    label: "Silent & stuck",
    icon: AlertOctagon,
    iconColor: "text-destructive",
    iconBg: "bg-destructive/15",
    textColor: "text-destructive",
    barColor: "bg-destructive",
    pulse: true,
  },
  IDLE: {
    label: "Idle",
    icon: Moon,
    iconColor: "text-muted-foreground",
    iconBg: "bg-white/5",
    textColor: "text-muted-foreground",
    barColor: "bg-white/20",
    pulse: false,
  },
};

export function healthAccentColor(state: HealthState): string {
  return HEALTH_HERO_META[state].barColor;
}

export function HealthHero({ state, className }: { state: HealthState; className?: string }) {
  const meta = HEALTH_HERO_META[state];
  const Icon = meta.icon;
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", meta.iconBg)}>
        <Icon className={cn("h-5 w-5", meta.iconColor, meta.pulse && "animate-pulse")} />
      </div>
      <p className={cn("text-base font-bold leading-tight", meta.textColor)}>{meta.label}</p>
    </div>
  );
}
