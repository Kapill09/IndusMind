import React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "@/lib/utils";
import {
  NODE_COLORS,
  DEFAULT_NODE_COLOR,
  NODE_ICONS,
} from "@/components/knowledge-graph/knowledge-graph-constants";
import type { KGNodeData } from "@/hooks/use-knowledge-graph";

/**
 * Custom React Flow node with enterprise styling.
 * Displays an icon, label, and type-colored accent.
 */
function GraphNodeInner({ data }: NodeProps) {
  const d = data as KGNodeData & {
    _isSelected?: boolean;
    _isConnected?: boolean;
    _isSearchMatch?: boolean;
    _opacity?: number;
  };

  const colors = NODE_COLORS[d.nodeType] ?? DEFAULT_NODE_COLOR;
  const Icon = NODE_ICONS[d.nodeType];
  const opacity = d._opacity ?? 1;

  return (
    <>
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2 !w-2 !border-2 !border-background !bg-muted-foreground/50"
      />
      <div
        className={cn(
          "group flex items-center gap-2.5 rounded-xl border px-3 py-2.5 shadow-sm transition-all duration-200",
          colors.bg,
          colors.bgDark,
          colors.border,
          colors.borderDark,
          d._isSelected && "ring-2 ring-primary ring-offset-2 ring-offset-background",
          d._isConnected && "ring-1 ring-primary/40 ring-offset-1 ring-offset-background"
        )}
        style={{
          opacity,
          transition: "opacity 0.3s ease, box-shadow 0.2s ease, transform 0.15s ease",
          minWidth: 140,
          maxWidth: 220,
        }}
      >
        {Icon && (
          <div
            className={cn(
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
              colors.text,
              colors.textDark,
              "bg-white/60 dark:bg-white/10"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p
            className={cn(
              "truncate text-xs font-semibold leading-tight",
              colors.text,
              colors.textDark
            )}
            title={d.label}
          >
            {d.label}
          </p>
          <p className="truncate text-[10px] leading-tight text-muted-foreground/70">
            {d.nodeType}
          </p>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2 !w-2 !border-2 !border-background !bg-muted-foreground/50"
      />
    </>
  );
}

export const GraphNode = React.memo(GraphNodeInner);
