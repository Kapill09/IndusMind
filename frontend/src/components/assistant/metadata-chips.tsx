import { Clock3, Cpu, FileText, Layers, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatMilliseconds } from "@/lib/utils";

interface MetadataChipsProps {
  latencyMs?: number;
  model?: string;
  contextChunks?: number;
  citationCount?: number;
}

export function MetadataChips({ latencyMs, model, contextChunks, citationCount }: MetadataChipsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {latencyMs !== undefined ? (
        <Badge variant="outline" className="text-muted-foreground bg-muted/30">
          <Clock3 className="mr-1.5 h-3 w-3" aria-hidden="true" />
          {formatMilliseconds(latencyMs)}
        </Badge>
      ) : null}

      {model ? (
        <Badge variant="outline" className="text-muted-foreground bg-muted/30">
          <Cpu className="mr-1.5 h-3 w-3" aria-hidden="true" />
          {model}
        </Badge>
      ) : null}

      {contextChunks !== undefined && contextChunks > 0 ? (
        <Badge variant="outline" className="text-muted-foreground bg-muted/30">
          <Layers className="mr-1.5 h-3 w-3" aria-hidden="true" />
          {contextChunks} Chunks
        </Badge>
      ) : null}

      {citationCount !== undefined && citationCount > 0 ? (
        <Badge variant="outline" className="text-muted-foreground bg-muted/30">
          <FileText className="mr-1.5 h-3 w-3" aria-hidden="true" />
          {citationCount} Citations
        </Badge>
      ) : null}
      
      {citationCount !== undefined && citationCount > 0 ? (
         <Badge variant="outline" className="text-primary border-primary/30 bg-primary/5">
         <ShieldCheck className="mr-1.5 h-3 w-3" aria-hidden="true" />
         Grounded
       </Badge>
      ) : null}
    </div>
  );
}
