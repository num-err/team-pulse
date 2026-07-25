import { CheckCircle2, Repeat, AlertOctagon, Moon, type LucideIcon } from "lucide-react";
import { Badge, type BadgeProps } from "@/components/ui/badge";

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
