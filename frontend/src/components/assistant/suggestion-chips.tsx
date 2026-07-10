import { useMemo } from "react";
import { Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { SUGGESTION_CHIPS } from "@/components/assistant/assistant-constants";

interface SuggestionChipsProps {
  onSuggest: (suggestion: string) => void;
  /** When provided, chips are contextual to the entities/question */
  entities?: Array<{ label: string; type: string }>;
  question?: string;
  disabled?: boolean;
}

export function SuggestionChips({ onSuggest, entities, question, disabled }: SuggestionChipsProps) {
  const chips = useMemo(() => {
    const list: string[] = [];

    // Entity-driven contextual chips
    if (entities?.length) {
      const equipment = entities.find((e) => e.type === "Equipment")?.label;
      const safety = entities.find((e) => e.type === "Safety")?.label;
      if (equipment) list.push(`Maintenance Procedure for ${equipment}`);
      if (safety) list.push(`Explain ${safety} procedures`);
    }

    // Question-context chips
    if (question) {
      const qLower = question.toLowerCase();
      if (qLower.includes("maintenance") || qLower.includes("lubricat")) {
        list.push("Show inspection intervals");
      }
      if (qLower.includes("error") || qLower.includes("fail")) {
        list.push("Troubleshooting steps");
      }
    }

    // Fill with generic chips
    for (const chip of SUGGESTION_CHIPS) {
      if (list.length >= 5) break;
      if (!list.includes(chip)) list.push(chip);
    }

    return list.slice(0, 5);
  }, [entities, question]);

  return (
    <div className="flex flex-wrap gap-2">
      {chips.map((chip, index) => (
        <motion.button
          key={chip}
          type="button"
          disabled={disabled}
          onClick={() => onSuggest(chip)}
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.18, delay: index * 0.04 }}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/30 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-all hover:border-primary/50 hover:bg-primary/5 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
        >
          <Sparkles className="h-3 w-3 text-primary" aria-hidden="true" />
          {chip}
        </motion.button>
      ))}
    </div>
  );
}
