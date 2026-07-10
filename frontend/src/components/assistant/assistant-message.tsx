import { memo, useState } from "react";
import { motion } from "framer-motion";
import {
  Bot,
  Clipboard,
  Check,
  RefreshCcw,
  ThumbsUp,
  ThumbsDown,
  FileSearch,
  Share2,
  Download,
} from "lucide-react";
import type { ChatMessage, RagSource } from "@/types";
import { ConfidenceBadge } from "./confidence-badge";
import { MetadataChips } from "./metadata-chips";
import { ReasoningPanel } from "./reasoning-panel";
import { EntityChips } from "./entity-chips";
import { SuggestionChips } from "./suggestion-chips";
import { MarkdownContent } from "@/components/assistant/markdown-content";
import { Button } from "@/components/ui/button";

interface AssistantMessageProps {
  message: ChatMessage;
  onSourceClick: (source: RagSource) => void;
  onViewSources: (sources: RagSource[]) => void;
  onSuggest: (suggestion: string) => void;
  onRegenerate: () => void;
  onCopy: (content: string) => void;
  onLike: () => void;
  onDislike: () => void;
  onOpenKnowledgeGraph: (entities?: Array<{ label: string; type: string }>) => void;
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  onViewSources,
  onSuggest,
  onRegenerate,
  onCopy,
  onLike,
  onDislike,
  onOpenKnowledgeGraph,
}: AssistantMessageProps) {
  const [copied, setCopied] = useState(false);
  const confidence = message.confidence ?? 72;
  const hasSources = message.sources && message.sources.length > 0;

  const handleCopy = () => {
    onCopy(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = () => {
    const blob = new Blob([message.content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `indusmind-answer-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24 }}
      className="flex items-start gap-3"
    >
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-card text-primary shadow-sm">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        {/* Answer content */}
        <div className="rounded-2xl rounded-tl-md border border-border bg-card p-4 shadow-sm sm:p-5">
          <MarkdownContent content={message.content} className="max-w-none" />
        </div>

        {/* Inline metadata row */}
        <div className="flex flex-wrap items-center gap-2">
          <ConfidenceBadge confidence={confidence} />
          <MetadataChips
            latencyMs={message.latencyMs}
            model={message.model}
            contextChunks={message.contextChunks}
            citationCount={message.sources?.length}
          />
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-emerald-500" aria-hidden="true" />
            ) : (
              <Clipboard className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {copied ? "Copied" : "Copy"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRegenerate}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            <RefreshCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Regenerate
          </Button>
          {hasSources && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewSources(message.sources!)}
              className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
            >
              <FileSearch className="h-3.5 w-3.5" aria-hidden="true" />
              Sources ({message.sources!.length})
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenKnowledgeGraph(message.entities)}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
            data-entities={JSON.stringify(message.entities ?? [])}
          >
            <Share2 className="h-3.5 w-3.5" aria-hidden="true" />
            Knowledge Graph
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExport}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            Export
          </Button>

          <div className="ml-auto flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={onLike}
              aria-label="Mark answer helpful"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-emerald-500"
            >
              <ThumbsUp className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDislike}
              aria-label="Mark answer not helpful"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-red-500"
            >
              <ThumbsDown className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          </div>
        </div>

        {/* Suggestion chips */}
        <SuggestionChips
          onSuggest={onSuggest}
          entities={message.entities ?? []}
          question={message.content}
        />

        {/* Entity chips */}
        <EntityChips
          entities={message.entities ?? []}
          onEntityClick={onSuggest}
        />

        {/* Reasoning panel */}
        <ReasoningPanel model={message.model} />
      </div>
    </motion.article>
  );
});
