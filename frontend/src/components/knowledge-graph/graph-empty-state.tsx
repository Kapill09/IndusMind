import { Share2, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";

interface GraphEmptyStateProps {
  onNavigateUpload?: () => void;
}

export function GraphEmptyState({ onNavigateUpload }: GraphEmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8">
      <div className="flex flex-col items-center text-center">
        {/* SVG Illustration — abstract network graph */}
        <div className="relative mb-6 flex h-32 w-32 items-center justify-center">
          <div className="absolute inset-0 animate-pulse rounded-full bg-primary/5" />
          <div className="absolute inset-3 rounded-full bg-primary/8" />
          <svg viewBox="0 0 120 120" className="h-24 w-24 text-muted-foreground/30">
            {/* Edges */}
            <line x1="60" y1="30" x2="30" y2="70" stroke="currentColor" strokeWidth="1.5" />
            <line x1="60" y1="30" x2="90" y2="55" stroke="currentColor" strokeWidth="1.5" />
            <line x1="30" y1="70" x2="75" y2="90" stroke="currentColor" strokeWidth="1.5" />
            <line x1="90" y1="55" x2="75" y2="90" stroke="currentColor" strokeWidth="1.5" />
            <line x1="30" y1="70" x2="90" y2="55" stroke="currentColor" strokeWidth="1" strokeDasharray="4 3" />
            {/* Nodes */}
            <circle cx="60" cy="30" r="8" className="fill-primary/20 stroke-primary/40" strokeWidth="1.5" />
            <circle cx="30" cy="70" r="6" className="fill-blue-400/20 stroke-blue-400/40" strokeWidth="1.5" />
            <circle cx="90" cy="55" r="7" className="fill-purple-400/20 stroke-purple-400/40" strokeWidth="1.5" />
            <circle cx="75" cy="90" r="5" className="fill-cyan-400/20 stroke-cyan-400/40" strokeWidth="1.5" />
          </svg>
          <Share2 className="absolute h-8 w-8 text-primary/40" />
        </div>

        <h3 className="text-lg font-semibold tracking-tight">
          No Knowledge Graph Available
        </h3>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
          Upload industrial documents to automatically build an AI-powered
          knowledge graph connecting equipment, procedures, and safety concepts.
        </p>

        {onNavigateUpload && (
          <Button className="mt-5 gap-2" onClick={onNavigateUpload}>
            <UploadCloud className="h-4 w-4" />
            Upload Documents
          </Button>
        )}
      </div>
    </div>
  );
}
