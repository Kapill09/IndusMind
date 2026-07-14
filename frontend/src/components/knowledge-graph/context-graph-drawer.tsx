import { useCallback, useRef } from "react";
import { ReactFlowProvider, type Node } from "@xyflow/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Share2,
  Sparkles,
  Loader2,
  AlertTriangle,
  MessageCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ChatMessage, PageKey, RagSource } from "@/types";
import type { KGNodeData } from "@/types/knowledge-graph";
import { useContextGraph } from "@/hooks/use-context-graph";
import { useGraphInteractions } from "@/hooks/use-graph-interactions";
import { GraphCanvas } from "@/components/knowledge-graph/graph-canvas";
import { GraphInspector } from "@/components/knowledge-graph/graph-inspector";

/* ──────────────────────────────────────────────────────────────────────── */
/*  Props                                                                  */
/* ──────────────────────────────────────────────────────────────────────── */

interface ContextGraphDrawerProps {
  /** The assistant message whose context graph to display. */
  message: ChatMessage | null;
  /** The original user question that produced this answer. */
  question: string;
  /** Close the drawer. */
  onClose: () => void;
  /** Navigate to a page (e.g. documents, assistant). */
  onNavigate?: (page: PageKey) => void;
  /** Open PDF viewer for a source. */
  onSourceClick?: (source: RagSource, contextSources?: RagSource[], confidence?: number) => void;
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Legend data                                                            */
/* ──────────────────────────────────────────────────────────────────────── */

const LEGEND_ITEMS: { type: string; label: string; dot: string }[] = [
  { type: "Question", label: "Question", dot: "bg-amber-500" },
  { type: "Document", label: "Document", dot: "bg-slate-500" },
  { type: "Problem Statements", label: "Problem Statement", dot: "bg-purple-500" },
  { type: "Technologies", label: "Technology", dot: "bg-cyan-500" },
  { type: "Equipment", label: "Equipment", dot: "bg-blue-500" },
  { type: "Standards", label: "Standards", dot: "bg-green-500" },
  { type: "SOPs", label: "SOP / Section", dot: "bg-indigo-500" },
  { type: "Safety terms", label: "Safety", dot: "bg-red-500" },
  { type: "Maintenance concepts", label: "Maintenance", dot: "bg-orange-500" },
  { type: "Regulations", label: "Regulations", dot: "bg-emerald-500" },
];

/* ──────────────────────────────────────────────────────────────────────── */
/*  Wrapper — provides ReactFlowProvider                                   */
/* ──────────────────────────────────────────────────────────────────────── */

export function ContextGraphDrawer(props: ContextGraphDrawerProps) {
  return (
    <AnimatePresence>
      {props.message && (
        <ReactFlowProvider>
          <ContextGraphDrawerInner {...props} />
        </ReactFlowProvider>
      )}
    </AnimatePresence>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Inner component                                                        */
/* ──────────────────────────────────────────────────────────────────────── */

function ContextGraphDrawerInner({
  message,
  question,
  onClose,
  onNavigate,
  onSourceClick,
}: ContextGraphDrawerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const {
    nodes,
    edges,
    rawEdges,
    stats,
    isLoading,
    isError,
    error,
    refetch,
    minimapColor,
  } = useContextGraph(message, question);

  const {
    selectedNode,
    connectedEdges,
    connectedNodes,
    styledNodes,
    visibleEdges,
    onNodeClick,
    onPaneClick,
    highlightRelated,
  } = useGraphInteractions({ allNodes: nodes, allEdges: edges, rawEdges });

  // Handle clicking a document node → open PDF viewer
  const handleNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const data = node.data as KGNodeData;
      if (data.type === "Document" && onSourceClick && message?.sources) {
        const matchedSource = message.sources.find(
          (s) =>
            s.metadata?.document_id === data.document ||
            s.metadata?.filename === data.label
        );
        if (matchedSource) {
          onSourceClick(matchedSource, message.sources, message.confidence);
        }
      }
    },
    [message, onSourceClick],
  );

  return (
    <motion.div
      key="context-graph-drawer"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-50 flex flex-col bg-background"
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="flex items-center justify-between border-b border-border bg-card/90 backdrop-blur-sm px-5 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Share2 className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold truncate">
                Context Knowledge Graph
              </h2>
              <Badge variant="secondary" className="text-[10px] shrink-0">
                <Sparkles className="mr-1 h-2.5 w-2.5" />
                Answer-Scoped
              </Badge>
            </div>
            <p className="mt-0.5 truncate text-xs text-muted-foreground max-w-lg">
              <MessageCircle className="mr-1 inline h-3 w-3" />
              {question || "AI Response"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Stats pills */}
          {stats.totalNodes > 0 && (
            <div className="hidden sm:flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className="rounded-full border border-border bg-background/60 px-2.5 py-1">
                {stats.totalNodes} nodes
              </span>
              <span className="rounded-full border border-border bg-background/60 px-2.5 py-1">
                {stats.totalEdges} edges
              </span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
            aria-label="Close context graph"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div ref={containerRef} className="relative flex flex-1 overflow-hidden">
        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-1 items-center justify-center">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="h-16 w-16 rounded-2xl border border-border bg-card shadow-lg flex items-center justify-center">
                  <Share2 className="h-6 w-6 text-primary animate-pulse" />
                </div>
                <Loader2 className="absolute -bottom-1 -right-1 h-5 w-5 animate-spin text-primary" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold">Building Context Graph</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Extracting entities and relationships from the answer…
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error state */}
        {isError && !isLoading && (
          <div className="flex flex-1 items-center justify-center">
            <div className="flex flex-col items-center gap-4 max-w-sm text-center">
              <div className="h-14 w-14 rounded-2xl border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950 flex items-center justify-center">
                <AlertTriangle className="h-6 w-6 text-red-500" />
              </div>
              <div>
                <p className="text-sm font-semibold">Failed to Build Graph</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {error instanceof Error ? error.message : "Unknown error"}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !isError && nodes.length === 0 && (
          <div className="flex flex-1 items-center justify-center">
            <div className="flex flex-col items-center gap-4 max-w-sm text-center">
              <div className="h-14 w-14 rounded-2xl border border-border bg-card flex items-center justify-center">
                <Share2 className="h-6 w-6 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-semibold">No Context Graph Available</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  This answer did not reference enough sources to build a knowledge graph.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Graph canvas */}
        {!isLoading && !isError && nodes.length > 0 && (
          <>
            <div className="relative flex-1 h-full">
              <GraphCanvas
                nodes={styledNodes}
                edges={visibleEdges}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                onNodeDoubleClick={handleNodeDoubleClick}
                minimapColor={minimapColor}
              />

              {/* Legend overlay */}
              <div className="absolute bottom-4 left-4 rounded-xl border border-border bg-card/90 backdrop-blur-sm p-3 shadow-lg max-w-xs">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Entity Types
                </p>
                <div className="flex flex-wrap gap-x-3 gap-y-1.5">
                  {LEGEND_ITEMS.filter(
                    (item) =>
                      stats.entityTypes[item.type] != null &&
                      stats.entityTypes[item.type] > 0
                  ).map((item) => (
                    <div
                      key={item.type}
                      className="flex items-center gap-1.5 text-[11px] text-muted-foreground"
                    >
                      <span className={`h-2 w-2 rounded-full ${item.dot}`} />
                      <span>
                        {item.label}
                        <span className="ml-0.5 text-[10px] opacity-60">
                          ({stats.entityTypes[item.type]})
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Inspector panel */}
            {selectedNode && (
              <GraphInspector
                node={selectedNode}
                connectedNodes={connectedNodes}
                connectedEdges={connectedEdges}
                onClose={onPaneClick}
                onHighlightRelated={highlightRelated}
                onNavigate={onNavigate}
              />
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}
