import { Bot, ExternalLink, Sparkles, X } from "lucide-react";
import type { Node } from "@xyflow/react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { KGNodeData } from "@/hooks/use-knowledge-graph";
import {
  NODE_COLORS,
  DEFAULT_NODE_COLOR,
  NODE_ICONS,
} from "@/components/knowledge-graph/knowledge-graph-constants";
import type { PageKey } from "@/types";

interface GraphInspectorProps {
  node: Node<KGNodeData> | null;
  connectedNodes: Node<KGNodeData>[];
  connectedEdges: { source: string; target: string; relationship: string; weight: number }[];
  onClose: () => void;
  onHighlightRelated: () => void;
  onNavigate?: (page: PageKey) => void;
}

export function GraphInspector({
  node,
  connectedNodes,
  connectedEdges,
  onClose,
  onHighlightRelated,
  onNavigate,
}: GraphInspectorProps) {
  if (!node) return null;

  const d = node.data as KGNodeData;
  const colors = NODE_COLORS[d.nodeType] ?? DEFAULT_NODE_COLOR;
  const Icon = NODE_ICONS[d.nodeType];

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-l border-border bg-card/50 lg:w-96">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-start justify-between border-b border-border p-4">
        <div className="flex items-center gap-3">
          {Icon && (
            <div
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-xl",
                colors.bg,
                colors.bgDark,
                colors.text,
                colors.textDark
              )}
            >
              <Icon className="h-4 w-4" />
            </div>
          )}
          <div className="min-w-0">
            <h3 className="text-sm font-semibold leading-tight">{d.label}</h3>
            <Badge variant="secondary" className="mt-1 text-[10px]">
              {d.nodeType}
            </Badge>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={onClose}
          aria-label="Close inspector"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* ── Details ─────────────────────────────────────────────── */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {/* Description */}
        <DetailSection title="Description">
          <p className="text-sm leading-relaxed text-muted-foreground">
            {d.description || "No description available."}
          </p>
        </DetailSection>

        {/* Metadata */}
        <DetailSection title="Metadata">
          <div className="space-y-2">
            <MetaRow label="Entity Type" value={d.nodeType} />
            {d.document && <MetaRow label="Document" value={d.document} />}
            {d.page != null && <MetaRow label="Page" value={String(d.page)} />}
            <MetaRow label="Node ID" value={d.originalId} mono />
          </div>
        </DetailSection>

        {/* Connected Entities */}
        <DetailSection
          title={`Connected Entities (${connectedNodes.length})`}
        >
          {connectedNodes.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No connected entities found.
            </p>
          ) : (
            <div className="max-h-48 space-y-1.5 overflow-y-auto">
              {connectedNodes.slice(0, 20).map((cn) => {
                const cData = cn.data as KGNodeData;
                const cColors = NODE_COLORS[cData.nodeType] ?? DEFAULT_NODE_COLOR;
                const edge = connectedEdges.find(
                  (e) =>
                    (e.source === node.id && e.target === cn.id) ||
                    (e.target === node.id && e.source === cn.id)
                );
                return (
                  <div
                    key={cn.id}
                    className="flex items-center justify-between rounded-lg border border-border bg-background/60 px-2.5 py-2"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={cn2(
                          "h-2 w-2 shrink-0 rounded-full",
                          cColors.bg,
                          cColors.bgDark
                        )}
                      />
                      <span className="truncate text-xs font-medium">
                        {cData.label}
                      </span>
                    </div>
                    {edge && (
                      <span className="ml-2 shrink-0 text-[10px] text-muted-foreground">
                        {edge.relationship}
                      </span>
                    )}
                  </div>
                );
              })}
              {connectedNodes.length > 20 && (
                <p className="pt-1 text-center text-[10px] text-muted-foreground">
                  +{connectedNodes.length - 20} more
                </p>
              )}
            </div>
          )}
        </DetailSection>
      </div>

      {/* ── Actions ─────────────────────────────────────────────── */}
      <div className="space-y-2 border-t border-border p-4">
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-2 text-xs"
          onClick={onHighlightRelated}
        >
          <Sparkles className="h-3 w-3" />
          Highlight Related Nodes
        </Button>
        {onNavigate && (
          <>
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-2 text-xs"
              onClick={() => onNavigate("documents")}
            >
              <ExternalLink className="h-3 w-3" />
              Open Source Document
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-2 text-xs"
              onClick={() => onNavigate("assistant")}
            >
              <Bot className="h-3 w-3" />
              Ask AI About This
            </Button>
          </>
        )}
      </div>
    </aside>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h4>
      {children}
    </div>
  );
}

function MetaRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="shrink-0 text-xs text-muted-foreground">{label}</span>
      <span
        className={cn2(
          "truncate text-xs font-medium text-right",
          mono && "font-mono text-[10px]"
        )}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

/**
 * Local alias to avoid collision with the `cn` import from utils
 * and the `connectedNodes` variable in the component scope.
 */
function cn2(...args: Parameters<typeof cn>) {
  return cn(...args);
}
