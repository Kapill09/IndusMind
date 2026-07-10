import { Sparkles, Settings, FileText, AlertTriangle, ListChecks, Shield, Settings2 } from "lucide-react";
import { motion } from "framer-motion";
import { EMPTY_PROMPTS } from "@/components/assistant/assistant-constants";

interface EmptyStateProps {
  onPrompt: (prompt: string) => void;
  disabled: boolean;
}

export function EmptyState({ onPrompt, disabled }: EmptyStateProps) {
  const icons = [Settings, Shield, FileText, AlertTriangle, ListChecks, Settings2];

  return (
    <div className="flex min-h-[500px] flex-col items-center justify-center text-center">
      <motion.div 
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ 
          type: "spring", 
          stiffness: 260, 
          damping: 20,
          delay: 0.1
        }}
        className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20"
      >
        <Sparkles className="h-8 w-8" aria-hidden="true" />
      </motion.div>
      
      <motion.h2 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-6 text-2xl font-semibold tracking-[-0.01em]"
      >
        Enterprise AI Copilot
      </motion.h2>
      
      <motion.p 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground"
      >
        Ask questions across your industrial knowledge base. Answers are grounded in uploaded manuals, SOPs, and inspection reports with verifiable citations.
      </motion.p>
      
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-10 grid w-full max-w-4xl gap-3 px-4 sm:grid-cols-2 md:grid-cols-3"
      >
        {EMPTY_PROMPTS.map((prompt, index) => {
          const Icon = icons[index];
          return (
            <button
              key={prompt}
              type="button"
              disabled={disabled}
              onClick={() => onPrompt(prompt)}
              className="group flex flex-col items-start gap-3 rounded-xl border border-border bg-card p-5 text-left transition-all hover:bg-muted/30 hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60 shadow-sm"
            >
              <div className="rounded-lg bg-muted p-2 text-muted-foreground group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </div>
              <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                {prompt}
              </span>
            </button>
          );
        })}
      </motion.div>
    </div>
  );
}
