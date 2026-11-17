import { cn } from "@/lib/utils";
import { SOURCE_META } from "@/components/source-icons";

const ORDER = ["github", "linear", "notion", "figma", "slack"];

export function IntegrationsStrip({ className }: { className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-x-6 gap-y-3", className)}>
      {ORDER.map((key) => {
        const { icon: Icon, label } = SOURCE_META[key];
        return (
          <span key={key} className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Icon className="h-4 w-4" />
            {label}
          </span>
        );
      })}
    </div>
  );
}
