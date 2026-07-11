import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { calculateConfidenceScore } from "@/lib/assistant-utils";
import type { RagSource } from "@/types";

interface ConfidenceBadgeProps {
  confidence: number;
  sources?: RagSource[] | null;
  contextChunks?: number;
  className?: string;
}

export function ConfidenceBadge({ confidence, sources, contextChunks, className }: ConfidenceBadgeProps) {
  const summary = calculateConfidenceScore(sources, { contextChunks });
  const resolvedScore = Math.max(0, Math.min(100, Math.round(confidence ?? summary.score)));
  const score = summary.score > 0 ? Math.round((resolvedScore + summary.score) / 2) : resolvedScore;

  let colorClass = "text-emerald-600 dark:text-emerald-500 border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/50";
  let dotClass = "bg-emerald-500";

  if (score < 60) {
    colorClass = "text-red-600 dark:text-red-500 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/50";
    dotClass = "bg-red-500";
  } else if (score < 80) {
    colorClass = "text-amber-600 dark:text-amber-500 border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/50";
    dotClass = "bg-amber-500";
  }

  const tooltipText = `Why confidence is ${score}% • Average Similarity ${Math.round(summary.breakdown.averageSimilarity * 100)}% • Retrieved Chunks ${summary.breakdown.retrievedChunks} • Metadata Match ${summary.breakdown.metadataMatch ? "Yes" : "No"}`;

  return (
    <Badge
      variant="outline"
      className={cn("gap-1.5 rounded-full px-2.5 py-0.5 shadow-sm font-medium", colorClass, className)}
      title={tooltipText}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dotClass)} aria-hidden="true" />
      {score >= 80 ? "HIGH" : score >= 60 ? "MEDIUM" : "LOW"} {score}%
    </Badge>
  );
}
