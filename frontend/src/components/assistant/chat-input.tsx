import type React from "react";
import { useRef } from "react";
import { Send, Paperclip, Share2 } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { DocumentSelector } from "@/components/documents/document-selector";
import { useToast } from "@/components/feedback/toast";

interface ChatInputProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  error?: string | null;
}

export function ChatInput({ onSubmit, isLoading, error }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const { notify } = useToast();

  const handleComingSoon = () => {
    notify({
      tone: "info",
      title: "Coming soon",
      description: "This feature will be available in a future update.",
    });
  };

  const handleSubmit = () => {
    const value = textareaRef.current?.value.trim();
    if (!value || isLoading) return;
    onSubmit(value);
    if (textareaRef.current) {
      textareaRef.current.value = "";
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="sticky bottom-0 z-10 border-t border-border bg-background/95 px-4 pb-4 pt-3 backdrop-blur supports-[backdrop-filter]:bg-background/80"
    >
      <div className="mx-auto max-w-[820px]">
        {error && (
          <div className="mb-3 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-2.5 text-sm text-destructive" role="alert">
            {error}
          </div>
        )}

        <div className="rounded-2xl border border-border bg-card shadow-enterprise transition-shadow focus-within:border-primary/40 focus-within:shadow-lg focus-within:shadow-primary/5">
          <textarea
            ref={textareaRef}
            aria-label="Ask the industrial copilot"
            placeholder="Ask about manuals, SOPs, inspections, maintenance..."
            disabled={isLoading}
            rows={1}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            className="block w-full resize-none bg-transparent px-4 pb-0 pt-4 text-sm leading-6 text-foreground placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          />

          <div className="flex items-center justify-between gap-2 px-3 pb-3 pt-2">
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleComingSoon}
                className="h-8 gap-1.5 px-2.5 text-xs text-muted-foreground"
                aria-label="Attach file"
                title="Attach file (coming soon)"
              >
                <Paperclip className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleComingSoon}
                className="h-8 gap-1.5 px-2.5 text-xs text-muted-foreground"
                aria-label="Knowledge Graph mode"
                title="Knowledge Graph mode (coming soon)"
              >
                <Share2 className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <div className="h-5 w-px bg-border" />
              <DocumentSelector compact />
            </div>

            <Button
              size="sm"
              disabled={isLoading}
              onClick={handleSubmit}
              className="h-8 gap-1.5 rounded-xl px-4"
            >
              <Send className="h-3.5 w-3.5" aria-hidden="true" />
              {isLoading ? "Working..." : "Send"}
            </Button>
          </div>
        </div>

        <p className="mt-2 text-center text-[11px] text-muted-foreground/60">
          IndusMind AI grounds answers in your uploaded documents. Always verify critical operational decisions.
        </p>
      </div>
    </motion.div>
  );
}
