import { memo } from "react";
import { FileText } from "lucide-react";
import type { RagSource } from "@/types";
import { Progress } from "@/components/ui/progress";

interface SourceCardProps {
  source: RagSource;
  onClick: (source: RagSource) => void;
}

export const SourceCard = memo(function SourceCard({ source, onClick }: SourceCardProps) {
  const filename = String(source.metadata.filename ?? "Uploaded document");
  const score = Math.max(0, Math.min(100, Math.round((source.score ?? 0.72) * 100)));
  const pageLabel = getPageLabel(source);
  const heading = source.metadata.heading || source.metadata.title || "Document snippet";

  return (
    <button
      type="button"
      onClick={() => onClick(source)}
      className="group w-full cursor-pointer overflow-hidden rounded-xl border border-border bg-background text-left transition-all hover:border-primary/50 hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={`Open source ${filename}, ${pageLabel}`}
    >
      <div className="p-3">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
            <FileText className="h-4 w-4" aria-hidden="true" />
          </div>

          <div className="min-w-0 flex-1 space-y-1">
            <h4 className="truncate text-xs font-semibold leading-tight text-foreground" title={filename}>
              {filename}
            </h4>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-medium text-muted-foreground">{pageLabel}</span>
              <div className="flex min-w-0 flex-1 items-center gap-1.5">
                <Progress value={score} className="h-1 flex-1 bg-muted group-hover:bg-muted/80" />
                <span className="text-[10px] font-medium text-muted-foreground">{score}%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-2.5 border-t border-border/50 pt-2.5">
          <p className="line-clamp-2 text-xs leading-5 text-muted-foreground">
            <strong className="font-medium text-foreground">{heading}</strong> -{" "}
            {source.text || "Grounded snippet from the uploaded document."}
          </p>
        </div>
      </div>
    </button>
  );
});

function getPageLabel(source: RagSource) {
  if (source.page_start && source.page_end) {
    return source.page_start === source.page_end
      ? `Page ${source.page_start}`
      : `Pages ${source.page_start}-${source.page_end}`;
  }

  if (source.page_start) return `Page ${source.page_start}`;
  if (source.page_end) return `Page ${source.page_end}`;
  return "Unknown page";
}
