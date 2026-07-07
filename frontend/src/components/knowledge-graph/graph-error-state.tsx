import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface GraphErrorStateProps {
  error: Error | null;
  onRetry: () => void;
}

export function GraphErrorState({ error, onRetry }: GraphErrorStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8">
      <div className="flex flex-col items-center text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h3 className="text-lg font-semibold tracking-tight">
          Failed to Load Knowledge Graph
        </h3>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
          {error?.message ||
            "An unexpected error occurred while fetching the knowledge graph. Please check your backend connection and try again."}
        </p>
        <Button className="mt-5 gap-2" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" />
          Retry
        </Button>
      </div>
    </div>
  );
}
