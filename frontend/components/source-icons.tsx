import { Github, GitBranch, FileText, Figma, Slack, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export const SOURCE_META: Record<string, { icon: LucideIcon; label: string }> = {
  github: { icon: Github, label: "GitHub" },
  linear: { icon: GitBranch, label: "Linear" },
  notion: { icon: FileText, label: "Notion" },
  figma: { icon: Figma, label: "Figma" },
  slack: { icon: Slack, label: "Slack" },
};

export function SourceIcons({ sources, className }: { sources?: string[]; className?: string }) {
  if (!sources?.length) return null;
  return (
    <div className={cn("flex items-center gap-1", className)}>
      {sources.map((source) => {
        const meta = SOURCE_META[source];
        if (!meta) return null;
        const Icon = meta.icon;
        return (
          <span
            key={source}
            title={meta.label}
            aria-label={meta.label}
            className="flex h-6 w-6 items-center justify-center rounded-md border bg-card text-muted-foreground"
          >
            <Icon className="h-3.5 w-3.5" />
          </span>
        );
      })}
    </div>
  );
}
