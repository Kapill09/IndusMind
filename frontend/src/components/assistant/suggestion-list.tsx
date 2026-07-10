import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMemo } from "react";

interface SuggestionListProps {
  question: string;
  entities: Array<{ label: string; type: string }>;
  onSuggest: (suggestion: string) => void;
}

export function SuggestionList({ question, entities, onSuggest }: SuggestionListProps) {
  const suggestions = useMemo(() => {
    const list = new Set<string>();
    
    // Entity-based suggestions
    const equipment = entities.find(e => e.type === "Equipment")?.label;
    const safety = entities.find(e => e.type === "Safety")?.label;
    
    if (equipment) {
      list.add(`Show maintenance checklist for ${equipment}`);
      list.add(`What are the safety precautions for ${equipment}?`);
    }
    
    if (safety) {
      list.add(`Explain ${safety} procedures in detail`);
    }

    // Question-based fallbacks
    const qLower = question.toLowerCase();
    if (qLower.includes("maintenance") || qLower.includes("lubricat")) {
      list.add("What are the inspection intervals?");
    }
    if (qLower.includes("error") || qLower.includes("fail") || qLower.includes("problem")) {
      list.add("Show troubleshooting steps");
    }
    
    // Generic fallbacks if we don't have enough
    if (list.size < 3) list.add("Explain this SOP");
    if (list.size < 3) list.add("Show related equipment");
    if (list.size < 3) list.add("What safety precautions exist?");
    
    return Array.from(list).slice(0, 3);
  }, [question, entities]);

  if (suggestions.length === 0) return null;

  return (
    <div className="mt-4 flex flex-wrap gap-2 pt-2">
      {suggestions.map(suggestion => (
        <Button 
          key={suggestion} 
          variant="outline" 
          size="sm" 
          onClick={() => onSuggest(suggestion)}
          className="rounded-full text-xs font-medium text-muted-foreground hover:text-foreground bg-muted/20"
        >
          <Sparkles className="mr-1.5 h-3 w-3 text-primary" />
          {suggestion}
        </Button>
      ))}
    </div>
  );
}
