import { Github, Slack, Figma, FileText, GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

const INTEGRATIONS = [
  { name: "GitHub", icon: Github },
  { name: "Linear", icon: GitBranch },
  { name: "Notion", icon: FileText },
  { name: "Figma", icon: Figma },
  { name: "Slack", icon: Slack },
];

export function IntegrationsStrip({ className }: { className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-center justify-center gap-3", className)}>
      {INTEGRATIONS.map(({ name, icon: Icon }) => (
        <div
          key={name}
          className="glass flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm text-muted-foreground"
        >
          <Icon className="h-4 w-4" />
          <span>{name}</span>
        </div>
      ))}
    </div>
  );
}
