import { useCallback, useState } from "react";
import { useReactFlow } from "@xyflow/react";
import { Download, Maximize2, Minimize2, RefreshCw, ScanSearch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface GraphToolbarProps {
  onRefresh: () => void;
  isRefreshing?: boolean;
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export function GraphToolbar({
  onRefresh,
  isRefreshing,
  containerRef,
}: GraphToolbarProps) {
  const { fitView } = useReactFlow();
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleFitView = useCallback(() => {
    fitView({ padding: 0.3, duration: 500 });
  }, [fitView]);

  const handleFullscreen = useCallback(async () => {
    const el = containerRef.current;
    if (!el) return;

    try {
      if (!document.fullscreenElement) {
        await el.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch {
      // Fullscreen not supported
    }
  }, [containerRef]);

  const handleExport = useCallback(() => {
    const svgEl = containerRef.current?.querySelector<SVGElement>(
      ".react-flow__renderer svg"
    );
    if (!svgEl) {
      // Fallback: export as JSON
      const data = JSON.stringify({ exported: true }, null, 2);
      const blob = new Blob([data], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "knowledge-graph-export.json";
      a.click();
      URL.revokeObjectURL(url);
      return;
    }

    const serializer = new XMLSerializer();
    const svgData = serializer.serializeToString(svgEl);
    const blob = new Blob([svgData], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "knowledge-graph.svg";
    a.click();
    URL.revokeObjectURL(url);
  }, [containerRef]);

  return (
    <div className="absolute right-4 top-4 z-10 flex items-center gap-1.5 rounded-xl border border-border bg-card/95 p-1 shadow-sm backdrop-blur">
      <ToolbarButton
        icon={RefreshCw}
        label="Refresh"
        onClick={onRefresh}
        className={cn(isRefreshing && "animate-spin")}
      />
      <ToolbarButton icon={ScanSearch} label="Fit Graph" onClick={handleFitView} />
      <ToolbarButton
        icon={isFullscreen ? Minimize2 : Maximize2}
        label={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
        onClick={handleFullscreen}
      />
      <ToolbarButton icon={Download} label="Export" onClick={handleExport} />
    </div>
  );
}

function ToolbarButton({
  icon: Icon,
  label,
  onClick,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  className?: string;
}) {
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={onClick}
      className="h-8 w-8"
      title={label}
      aria-label={label}
    >
      <Icon className={cn("h-3.5 w-3.5", className)} />
    </Button>
  );
}
