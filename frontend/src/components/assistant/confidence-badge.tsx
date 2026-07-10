import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  confidence: number;
  className?: string;
}

export function ConfidenceBadge({ confidence, className }: ConfidenceBadgeProps) {
  let colorClass = "text-emerald-600 dark:text-emerald-500 border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/50";
  let dotClass = "bg-emerald-500";

  if (confidence < 60) {
    colorClass = "text-red-600 dark:text-red-500 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/50";
    dotClass = "bg-red-500";
  } else if (confidence < 80) {
    colorClass = "text-amber-600 dark:text-amber-500 border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/50";
    dotClass = "bg-amber-500";
  }

  return (
    <Badge variant="outline" className={cn("gap-1.5 rounded-full px-2.5 py-0.5 shadow-sm font-medium", colorClass, className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dotClass)} aria-hidden="true" />
      Confidence {Math.round(confidence)}%
    </Badge>
  );
}
