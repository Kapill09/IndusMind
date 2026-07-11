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
  Sparkles,
} from "lucide-react";
import type { ChatMessage, RagSource } from "@/types";
import { ConfidenceBadge } from "./confidence-badge";
import { MetadataChips } from "./metadata-chips";
import { ReasoningPanel } from "./reasoning-panel";
import { EntityChips } from "./entity-chips";
import { SuggestionChips } from "./suggestion-chips";
import { MarkdownContent } from "@/components/assistant/markdown-content";
import { Button } from "@/components/ui/button";
import { buildStructuredAnswerSections } from "@/lib/assistant-utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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
  const structuredSections = buildStructuredAnswerSections(message.content, message.sources);
  const insightMetrics = [
    { label: "Documents Searched", value: message.sources?.length ? `${message.sources.length}` : "—" },
    { label: "Retrieved Chunks", value: `${message.contextChunks ?? message.sources?.length ?? 0}` },
    { label: "Average Similarity", value: `${Math.round(((message.sources ?? []).reduce((sum, source) => sum + (source.score ?? 0.72), 0) / Math.max(1, message.sources?.length ?? 1)) * 100)}%` },
    { label: "Grounded Answer", value: hasSources ? "Yes" : "Partial" },
    { label: "Response Time", value: `${message.latencyMs ?? 0} ms` },
    { label: "Model", value: message.model ?? "Gemini 2.5 Flash" },
  ];

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

        <div className="flex flex-wrap items-center gap-2">
          <ConfidenceBadge confidence={confidence} sources={message.sources} contextChunks={message.contextChunks} />
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

        <SuggestionChips
          onSuggest={onSuggest}
          entities={message.entities ?? []}
          question={message.content}
        />

        <EntityChips
          entities={message.entities ?? []}
          onEntityClick={onSuggest}
        />

        {hasSources && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground">Enterprise Citations</h4>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {message.sources!.slice(0, 4).map((source) => (
                <div key={source.chunk_id} className="rounded-2xl border border-border/70 bg-background/80 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{source.metadata?.filename ?? "Uploaded document"}</p>
                  <p className="mt-1 text-sm font-semibold text-foreground">{source.metadata?.heading || source.metadata?.title || "Source citation"}</p>
                  <p className="mt-2 text-[11px] text-muted-foreground">{source.text ? source.text.slice(0, 100) + (source.text.length > 100 ? "…" : "") : "Context preview unavailable."}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                    <span>{source.page_start ? `Page ${source.page_start}` : "Page unknown"}</span>
                    <span>•</span>
                    <span>{Math.round((source.score ?? 0.72) * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <ReasoningPanel model={message.model} />
      </div>
    </motion.article>
  );
});
