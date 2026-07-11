import { memo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Copy, FileText, ScanText, Sparkles } from "lucide-react";
import type { RagSource } from "@/types";
import { Progress } from "@/components/ui/progress";
import { getPageLabel, getSourcePreviewText } from "@/lib/assistant-utils";
import { buildCitationText } from "@/lib/assistant-utils";

interface SourceCardProps {
  source: RagSource;
  onClick: (source: RagSource) => void;
}

export const SourceCard = memo(function SourceCard({ source, onClick }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const filename = String(source.metadata.filename ?? "Uploaded document");
  const score = Math.max(0, Math.min(100, Math.round((source.score ?? 0.72) * 100)));
  const pageLabel = getPageLabel(source);
  const heading = source.metadata.heading || source.metadata.title || "Document snippet";
  const preview = getSourcePreviewText(source);
  const retrievalMethod = getRetrievalMethod(source);

  const handleClick = () => {
    setExpanded((value) => !value);
    onClick(source);
  };

  return (
    <motion.button
      type="button"
      onClick={handleClick}
      whileHover={{ y: -2, scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      className="group w-full cursor-pointer overflow-hidden rounded-2xl border border-border bg-background text-left shadow-sm transition-all hover:border-primary/50 hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={`Open source ${filename}, ${pageLabel}`}
    >
      <div className="p-3">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
            <FileText className="h-4 w-4" aria-hidden="true" />
          </div>

          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h4 className="truncate text-xs font-semibold leading-tight text-foreground" title={filename}>
                  {filename}
                </h4>
                <p className="mt-1 text-[11px] text-muted-foreground">{heading}</p>
              </div>
              <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                {retrievalMethod}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-medium text-muted-foreground">{pageLabel}</span>
              <div className="flex min-w-0 flex-1 items-center gap-1.5">
                <Progress value={score} className="h-1 flex-1 bg-muted group-hover:bg-muted/80" />
                <span className="text-[10px] font-medium text-muted-foreground">{score}%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-3 rounded-xl border border-border/60 bg-card/80 p-2.5">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            <ScanText className="h-3.5 w-3.5" aria-hidden="true" />
            Preview
          </div>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{preview}</p>
        </div>

        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-3 space-y-2 rounded-xl border border-border/70 bg-muted/20 p-2.5 text-xs text-muted-foreground">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-foreground">
                  <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  Citation
                </div>
                <p className="leading-5">{buildCitationText(source)}</p>
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                  Double-click to inspect the citation details.
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
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
