import { memo } from "react";
import { motion } from "framer-motion";
import { Clipboard, RefreshCcw, ThumbsDown, ThumbsUp, Sparkles } from "lucide-react";
import type { ChatMessage, RagSource } from "@/types";
import { ConfidenceBadge } from "./confidence-badge";
import { MetadataChips } from "./metadata-chips";
import { SourceCard } from "./source-card";
import { ReasoningPanel } from "./reasoning-panel";
import { SuggestionList } from "./suggestion-list";
import { EntityChips } from "./entity-chips";
import { Bot } from "lucide-react";
import { MarkdownContent } from "@/components/assistant/markdown-content";
import { Button } from "@/components/ui/button";
import { buildStructuredAnswerSections } from "@/lib/assistant-utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface AIResponseCardProps {
  message: ChatMessage;
  onSourceClick: (source: RagSource) => void;
  onSuggest: (suggestion: string) => void;
  onRegenerate: () => void;
  onCopy: (content: string) => void;
  onLike: () => void;
  onDislike: () => void;
}

export const AIResponseCard = memo(function AIResponseCard({
  message,
  onSourceClick,
  onSuggest,
  onRegenerate,
  onCopy,
  onLike,
  onDislike,
}: AIResponseCardProps) {
  const confidence = message.confidence ?? 72;
  const hasSources = message.sources && message.sources.length > 0;
  const structuredSections = buildStructuredAnswerSections(message.content, message.sources);
  const insightMetrics = [
    { label: "Documents Searched", value: message.sources?.length ? `${message.sources.length}` : "—" },
    { label: "Retrieved Chunks", value: `${message.contextChunks ?? message.sources?.length ?? 0}` },
    { label: "Average Similarity", value: `${Math.round(((message.sources ?? []).reduce((sum, source) => sum + (source.score ?? 0.72), 0) / Math.max(1, message.sources?.length ?? 1)) * 100)}%` },
    { label: "Grounded Answer", value: hasSources ? "Yes" : "Partial" },
    { label: "Response Time", value: `${message.latencyMs ?? 0} ms` },
    { label: "Model", value: message.model ?? "Gemini 2.5 Flash" },
  ];

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24 }}
      className="flex items-start gap-3"
    >
      <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-secondary text-secondary-foreground">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>

      <div className="w-full rounded-2xl border border-border bg-card p-4 shadow-enterprise sm:p-5">
        <div className="mb-5 space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <ConfidenceBadge confidence={confidence} sources={message.sources} contextChunks={message.contextChunks} />
            <MetadataChips
              latencyMs={message.latencyMs}
              model={message.model}
              contextChunks={message.contextChunks}
              citationCount={message.sources?.length}
            />
          </div>

          <Card className="overflow-hidden border-border/70 bg-muted/10">
            <CardHeader className="border-b border-border/60 bg-background/80">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
                <CardTitle className="text-sm">Structured AI Report</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4 sm:pt-5">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {structuredSections.map((section) => (
                  <div key={section.id} className="rounded-2xl border border-border/70 bg-background/80 p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{section.title}</p>
                    <p className="mt-2 line-clamp-4 text-sm leading-6 text-foreground">{section.content}</p>
                  </div>
                ))}
              </div>
              <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
                <MarkdownContent content={message.content} className="max-w-none" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-wrap gap-2 border-b border-border pb-4">
          <Button variant="outline" size="sm" onClick={() => onCopy(message.content)}>
            <Clipboard className="h-4 w-4" aria-hidden="true" />
            Copy
          </Button>
          <Button variant="outline" size="sm" onClick={onRegenerate}>
            <RefreshCcw className="h-4 w-4" aria-hidden="true" />
            Regenerate
          </Button>
          <Button variant="secondary" size="icon" onClick={onLike} aria-label="Mark answer helpful">
            <ThumbsUp className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button variant="secondary" size="icon" onClick={onDislike} aria-label="Mark answer not helpful">
            <ThumbsDown className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        <SuggestionList
          question={message.content}
          entities={message.entities || []}
          onSuggest={onSuggest}
        />

        <EntityChips
          entities={message.entities || []}
          onEntityClick={onSuggest}
        />

        <div className="mt-6 space-y-4 border-t border-border pt-5">
          <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">AI Insight</p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {insightMetrics.map((metric) => (
                <div key={metric.label} className="rounded-xl border border-border/70 bg-card/80 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{metric.label}</p>
                  <p className="mt-2 text-sm font-semibold text-foreground">{metric.value}</p>
                </div>
              ))}
            </div>
          </div>

          <h4 className="text-sm font-semibold text-foreground">Enterprise Citations</h4>
          {hasSources ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {message.sources!.slice(0, 4).map((source) => (
                <SourceCard
                  key={source.chunk_id}
                  source={source}
                  onClick={onSourceClick}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border bg-muted/20 p-4 text-sm text-muted-foreground">
              No citations were returned for this answer.
            </div>
          )}
        </div>

        <ReasoningPanel model={message.model} />
      </div>
    </motion.article>
  );
});
