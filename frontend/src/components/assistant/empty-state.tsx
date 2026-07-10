import { Bot, Sparkles, FileText, Clock } from "lucide-react";
import { motion } from "framer-motion";
import { SuggestionChips } from "@/components/assistant/suggestion-chips";
import { EMPTY_PROMPTS } from "@/components/assistant/assistant-constants";

interface EmptyStateProps {
  onPrompt: (prompt: string) => void;
  disabled: boolean;
}

export function EmptyState({ onPrompt, disabled }: EmptyStateProps) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      {/* AI Icon */}
      <motion.div
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{
          type: "spring",
          stiffness: 260,
          damping: 20,
          delay: 0.05,
        }}
        className="relative"
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-lg ring-1 ring-primary/20">
          <Bot className="h-8 w-8" aria-hidden="true" />
        </div>
        <motion.div
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm"
        >
          <Sparkles className="h-3 w-3" aria-hidden="true" />
        </motion.div>
      </motion.div>

      {/* Title */}
      <motion.h2
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mt-6 text-2xl font-semibold tracking-tight text-foreground"
      >
        IndusMind AI
      </motion.h2>

      {/* Description */}
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="mt-3 max-w-lg text-sm leading-6 text-muted-foreground"
      >
        Ask questions across your industrial knowledge base. Answers are grounded
        in uploaded manuals, SOPs, and inspection reports with verifiable
        citations.
      </motion.p>

      {/* Feature pills */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="mt-6 flex flex-wrap items-center justify-center gap-2"
      >
        {[
          { icon: FileText, label: "RAG-Grounded" },
          { icon: Sparkles, label: "Citation-Verified" },
          { icon: Clock, label: "Real-time Retrieval" },
        ].map((feature) => (
          <span
            key={feature.label}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/30 px-3 py-1 text-[11px] font-medium text-muted-foreground"
          >
            <feature.icon className="h-3 w-3 text-primary" aria-hidden="true" />
            {feature.label}
          </span>
        ))}
      </motion.div>

      {/* Suggested prompts */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45 }}
        className="mt-10 w-full max-w-2xl"
      >
        <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Try asking
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          {EMPTY_PROMPTS.map((prompt, index) => (
            <motion.button
              key={prompt}
              type="button"
              disabled={disabled}
              onClick={() => onPrompt(prompt)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.05 }}
              className="group flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground transition-all hover:border-primary/40 hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
            >
              <Sparkles className="h-3.5 w-3.5 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" aria-hidden="true" />
              <span className="line-clamp-1">{prompt}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
