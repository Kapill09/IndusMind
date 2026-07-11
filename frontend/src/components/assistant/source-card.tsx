import { memo, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, FileText, ScanText, Sparkles, Target } from "lucide-react";
import type { MouseEvent } from "react";
import type { RagSource } from "@/types";
import { Progress } from "@/components/ui/progress";
import { buildCitationText, getPageLabel, getSourcePreviewText, getSourceFilename, getSourceTitle } from "@/lib/assistant-utils";

interface SourceCardProps {
  source: RagSource;
  onClick: (source: RagSource) => void;
}

export const SourceCard = memo(function SourceCard({ source, onClick }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const title = getSourceTitle(source);
  const filename = getSourceFilename(source);
  const score = Math.max(0, Math.min(100, Math.round((source.score ?? 0.72) * 100)));
  const pageLabel = getPageLabel(source);
  const preview = getSourcePreviewText(source, 140);
  const retrievalMethod = getRetrievalMethod(source);

  const handleCardClick = () => {
    setIsExpanded((current) => !current);
    onClick(source);
  };

  const handleActionClick = (event: React.MouseEvent<HTMLButtonElement>, action: string) => {
    event.stopPropagation();
    if (action === "open") {
      onClick(source);
    } else if (action === "pdf") {
      onClick(source);
    } else if (action === "highlight") {
      onClick(source);
    }
  };

  const badgeLabel = useMemo(() => {
    if (retrievalMethod) return retrievalMethod;
    return score >= 85 ? "Semantic" : score >= 65 ? "Hybrid" : "Mixed";
  }, [retrievalMethod, score]);

  return (
    <motion.button
      type="button"
      onClick={handleCardClick}
      whileHover={{ y: -2, scale: 1.005 }}
      whileTap={{ scale: 0.99 }}
      className="group w-full cursor-pointer overflow-hidden rounded-3xl border border-border bg-background text-left shadow-enterprise transition-all duration-200 hover:border-primary/60 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={`Open source ${title}, ${pageLabel}`}
    >
      <div className="flex h-full flex-col p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
            <FileText className="h-5 w-5" aria-hidden="true" />
          </div>

          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground" title={filename}>
                  {filename}
                </p>
                <h3 className="mt-1 truncate text-sm font-semibold leading-6 text-foreground" title={title}>
                  {title}
                </h3>
              </div>
              <span className="rounded-full border border-border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                {badgeLabel}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
              <span>{pageLabel}</span>
              <span aria-hidden="true">•</span>
              <span>{score}% relevance</span>
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-[26px] border border-border/70 bg-card/90 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            <ScanText className="h-4 w-4" aria-hidden="true" />
            Source excerpt
          </div>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">{preview}</p>
        </div>

        <div className="mt-4 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
            <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
            Citation details
          </div>
          <p className="line-clamp-2 text-sm leading-6 text-foreground">{buildCitationText(source)}</p>
        </div>

        <div className="mt-5 flex flex-wrap gap-2 opacity-0 transition duration-200 group-hover:opacity-100">
          <button
            type="button"
            onClick={(event) => handleActionClick(event, "open")}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/80 px-3 py-2 text-[11px] font-semibold text-foreground transition hover:border-primary/70 hover:bg-primary/10"
          >
            <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            Open source
          </button>
          <button
            type="button"
            onClick={(event) => handleActionClick(event, "pdf")}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/80 px-3 py-2 text-[11px] font-semibold text-foreground transition hover:border-primary/70 hover:bg-primary/10"
          >
            <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            Open PDF
          </button>
          <button
            type="button"
            onClick={(event) => handleActionClick(event, "highlight")}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/80 px-3 py-2 text-[11px] font-semibold text-foreground transition hover:border-primary/70 hover:bg-primary/10"
          >
            <Target className="h-3.5 w-3.5" aria-hidden="true" />
            Highlight in KG
          </button>
        </div>
      </div>
    </motion.button>
  );
});

function getRetrievalMethod(source: RagSource) {
  const metadata = source.metadata ?? {};
  if (metadata.retrieval_method) return String(metadata.retrieval_method);
  if (metadata.structured) return "Structured";
  if (metadata.hybrid) return "Hybrid";
  if (source.score && source.score >= 0.9) return "Semantic";
  return "Hybrid";
}
