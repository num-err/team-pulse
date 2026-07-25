import { Github, GitBranch, FileText, Figma, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const SOURCE_META: Record<string, { icon: LucideIcon; label: string }> = {
  github: { icon: Github, label: "GitHub" },
  linear: { icon: GitBranch, label: "Linear" },
  notion: { icon: FileText, label: "Notion" },
  figma: { icon: Figma, label: "Figma" },
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
          <div
            key={source}
            title={meta.label}
            className="flex h-5 w-5 items-center justify-center rounded-full border border-white/10 bg-white/5 text-muted-foreground"
          >
            <Icon className="h-3 w-3" />
          </div>
        );
      })}
    </div>
  );
}
