import { memo } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { AIResponseCard } from "@/components/assistant/ai-response-card";
import { QUICK_ACTIONS } from "@/components/assistant/assistant-constants";
import type { ChatMessage, RagSource } from "@/types";

interface AssistantContentPanelProps {
  messages: ChatMessage[];
  onSourceClick: (source: RagSource) => void;
  onSuggest: (suggestion: string) => void;
  onRegenerate: () => void;
  onCopy: (content: string) => void;
  onLike: () => void;
  onDislike: () => void;
}

export const AssistantContentPanel = memo(function AssistantContentPanel({
  messages,
  onSourceClick,
  onSuggest,
  onRegenerate,
  onCopy,
  onLike,
  onDislike,
}: AssistantContentPanelProps) {
  return (
    <section className="flex min-h-0 flex-1 flex-col gap-5 overflow-hidden rounded-2xl border border-border bg-card/95 p-4 shadow-xl shadow-black/10">
      <div className="flex flex-col gap-4 rounded-2xl border border-border bg-muted/30 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Copilot interaction</p>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">Industrial AI Copilot</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Ask grounded operational questions and inspect every citation, confidence signal, and response metric.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button variant="secondary" size="sm" onClick={() => onSuggest(QUICK_ACTIONS[2])}>Related concepts</Button>
          <Button variant="outline" size="sm" onClick={() => onSuggest(QUICK_ACTIONS[1])}>Summarize</Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-1" aria-live="polite">
        {messages.map((message) =>
          message.role === "assistant" ? (
            <AIResponseCard
              key={message.id}
              message={message}
              onSourceClick={onSourceClick}
              onSuggest={onSuggest}
              onRegenerate={onRegenerate}
              onCopy={onCopy}
              onLike={onLike}
              onDislike={onDislike}
            />
          ) : (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
              className="max-w-[min(88%,760px)] self-end rounded-2xl border border-border bg-primary/10 p-4 shadow-enterprise"
            >
              <p className="whitespace-pre-wrap text-sm leading-7 text-foreground">{message.content}</p>
            </motion.div>
          ),
        )}
      </div>
    </section>
  );
});
