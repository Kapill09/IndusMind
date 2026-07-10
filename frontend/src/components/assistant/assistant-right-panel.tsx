import { memo } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Clock3, Database, FileText, Layers, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfidenceBadge } from "@/components/assistant/confidence-badge";
import { QUICK_ACTIONS } from "@/components/assistant/assistant-constants";
import type { ChatMessage, RagSource } from "@/types";
import { formatMilliseconds } from "@/lib/utils";

interface AssistantRightPanelProps {
  latestAnswer: ChatMessage | null;
  onSourceClick: (source: RagSource) => void;
  onQuickAction: (suggestion: string) => void;
}

export const AssistantRightPanel = memo(function AssistantRightPanel({
  latestAnswer,
  onSourceClick,
  onQuickAction,
}: AssistantRightPanelProps) {
  const sources = latestAnswer?.sources ?? [];
  const topSources = sources.slice(0, 3);

  return (
    <aside className="flex min-h-0 flex-col gap-4 rounded-2xl border border-border bg-card/95 p-4 shadow-xl shadow-black/10 backdrop-blur-xl">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Workspace insights</p>
            <h2 className="mt-1 text-xl font-semibold text-foreground">Sources & Metrics</h2>
          </div>
          <Badge variant="outline" className="bg-muted/30 text-muted-foreground">
            {latestAnswer ? "Live" : "Idle"}
          </Badge>
        </div>

        <Card className="space-y-4 rounded-2xl border-border bg-muted/20 p-4 shadow-none">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Latest answer</p>
              <p className="mt-2 text-sm font-semibold text-foreground">
                {latestAnswer ? "Operational summary" : "No answer yet"}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <Badge variant="outline" className="bg-background text-muted-foreground">
                {sources.length} sources
              </Badge>
              <Badge variant="outline" className="max-w-40 truncate bg-background text-muted-foreground">
                {latestAnswer?.model ?? "Model unavailable"}
              </Badge>
            </div>
          </div>

          {latestAnswer ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-border bg-background p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Confidence</p>
                <div className="mt-2 flex items-center gap-2">
                  <ConfidenceBadge confidence={latestAnswer.confidence ?? 0} />
                </div>
              </div>
              <div className="rounded-2xl border border-border bg-background p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Latency</p>
                <p className="mt-2 text-lg font-semibold text-foreground">
                  {formatMilliseconds(latestAnswer.latencyMs ?? 0)}
                </p>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border bg-background p-4 text-sm text-muted-foreground">
              Metrics appear here after the assistant returns an answer.
            </div>
          )}
        </Card>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Retrieved context</p>
            <h3 className="mt-1 text-base font-semibold text-foreground">Top grounded sources</h3>
          </div>
          <span className="text-xs text-muted-foreground">Click to inspect</span>
        </div>

        <div className="space-y-3">
          {topSources.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-muted/20 p-4 text-sm text-muted-foreground">
              Retrieved source snippets will appear here after an answer is generated.
            </div>
          ) : (
            topSources.map((source) => (
              <button
                type="button"
                key={source.chunk_id}
                onClick={() => onSourceClick(source)}
                className="group flex w-full flex-col gap-3 rounded-2xl border border-border bg-background p-4 text-left transition hover:border-primary hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-foreground">
                      {source.metadata.heading || source.metadata.title || "Document source"}
                    </p>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {source.metadata.filename ?? "Unknown document"} / Page {source.page_start ?? "unknown"}
                    </p>
                  </div>
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground transition group-hover:text-primary" aria-hidden="true" />
                </div>
                <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
                  {source.text ?? "No snippet available."}
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Quick actions</p>
          <ArrowRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
          {QUICK_ACTIONS.map((action) => (
            <Button
              key={action}
              variant="outline"
              size="sm"
              onClick={() => onQuickAction(action)}
              className="h-auto min-h-8 justify-start whitespace-normal rounded-xl text-left hover:border-primary"
            >
              <Sparkles className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              {action}
            </Button>
          ))}
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28 }}
        className="rounded-2xl border border-border bg-muted/20 p-4"
      >
        <div className="flex items-center gap-2 text-muted-foreground">
          <Layers className="h-4 w-4 text-primary" aria-hidden="true" />
          <p className="text-xs font-semibold uppercase tracking-[0.18em]">System status</p>
        </div>
        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>Knowledge indexed from approved documents</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock3 className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>Response lifecycle tracked with operational transparency</span>
          </div>
        </div>
      </motion.div>
    </aside>
  );
});
