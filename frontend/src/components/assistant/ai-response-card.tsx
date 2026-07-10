import { memo } from "react";
import { motion } from "framer-motion";
import { Clipboard, RefreshCcw, ThumbsDown, ThumbsUp } from "lucide-react";
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
            <ConfidenceBadge confidence={confidence} />
            <MetadataChips
              latencyMs={message.latencyMs}
              model={message.model}
              contextChunks={message.contextChunks}
              citationCount={message.sources?.length}
            />
          </div>

          <div className="rounded-2xl border border-border bg-muted/20 p-4">
            <MarkdownContent content={message.content} className="max-w-none" />
          </div>
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

        <div className="mt-6 border-t border-border pt-5">
          <h4 className="mb-3 text-sm font-semibold text-foreground">Grounded Sources</h4>
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
