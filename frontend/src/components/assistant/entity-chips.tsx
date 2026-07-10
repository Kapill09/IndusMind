import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface EntityChipsProps {
  entities: Array<{ label: string; type: string }>;
  onEntityClick: (entity: string) => void;
}

const ENTITY_COLORS: Record<string, string> = {
  Equipment: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  Safety: "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
  Maintenance: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800",
  Standards: "bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800",
  Technologies: "bg-indigo-100 text-indigo-700 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800",
  SOPs: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800",
};

export function EntityChips({ entities, onEntityClick }: EntityChipsProps) {
  if (!entities || entities.length === 0) return null;

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <p className="text-xs font-semibold text-muted-foreground mb-2">Related Entities</p>
      <div className="flex flex-wrap gap-2">
        {entities.map(entity => {
          const colorClass = ENTITY_COLORS[entity.type] || "bg-muted text-muted-foreground border-border";
          
          return (
            <button
              key={`${entity.type}-${entity.label}`}
              onClick={() => onEntityClick(`Tell me about ${entity.label}`)}
              className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-full"
            >
              <Badge 
                variant="outline" 
                className={cn("hover:opacity-80 transition-opacity cursor-pointer text-[11px]", colorClass)}
              >
                {entity.label}
              </Badge>
            </button>
          );
        })}
      </div>
    </div>
  );
}
