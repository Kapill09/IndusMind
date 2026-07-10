import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ReasoningPanelProps {
  model?: string;
}

export function ReasoningPanel({ model }: ReasoningPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  const steps = [
    { title: "Query Embedding", description: "Converted question to semantic vector space" },
    { title: "Vector Search", description: "Scanned ChromaDB for nearest document chunks" },
    { title: "Chunk Ranking", description: "Applied hybrid ranking (semantic + keyword)" },
    { title: "LLM Generation", description: `Generated answer${model ? ` using ${model}` : ""}` },
    { title: "Citation Grounding", description: "Mapped generated facts back to source chunks" }
  ];

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-border bg-card">
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between bg-muted/20 px-4 py-3 text-sm font-medium hover:bg-muted/40 transition-colors"
      >
        <span className="flex items-center gap-2 text-muted-foreground">
          How this answer was generated
        </span>
        {isOpen ? <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden="true" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />}
      </button>
      
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="border-t border-border p-4">
              <div className="space-y-3 pl-1">
                {steps.map((step, index) => (
                  <div key={index} className="flex gap-3 relative">
                    {index < steps.length - 1 && (
                      <div className="absolute left-[9px] top-5 bottom-[-10px] w-[2px] bg-border/50" />
                    )}
                    <div className="mt-0.5 shrink-0 relative z-10 bg-card rounded-full">
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{step.title}</p>
                      <p className="text-xs text-muted-foreground">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
