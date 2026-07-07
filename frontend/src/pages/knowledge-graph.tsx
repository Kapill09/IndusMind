import { useCallback, useRef, useState } from "react";
import { ReactFlowProvider, useReactFlow, type Node } from "@xyflow/react";
import { motion } from "framer-motion";
import { Share2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useKnowledgeGraph, type KGNodeData } from "@/hooks/use-knowledge-graph";
import { useGraphInteractions } from "@/hooks/use-graph-interactions";
import { GraphCanvas } from "@/components/knowledge-graph/graph-canvas";
import { GraphToolbar } from "@/components/knowledge-graph/graph-toolbar";
import { GraphSidebar } from "@/components/knowledge-graph/graph-sidebar";
import { GraphInspector } from "@/components/knowledge-graph/graph-inspector";
import { GraphEmptyState } from "@/components/knowledge-graph/graph-empty-state";
import { GraphErrorState } from "@/components/knowledge-graph/graph-error-state";
import { GraphLoadingState } from "@/components/knowledge-graph/graph-loading-state";
import { GraphContextMenu } from "@/components/knowledge-graph/graph-context-menu";
import type { PageKey } from "@/types";

interface KnowledgeGraphPageProps {
  onNavigate?: (page: PageKey) => void;
}

export function KnowledgeGraphPage({ onNavigate }: KnowledgeGraphPageProps) {
  return (
    <ReactFlowProvider>
      <KnowledgeGraphContent onNavigate={onNavigate} />
    </ReactFlowProvider>
  );
}

function KnowledgeGraphContent({ onNavigate }: KnowledgeGraphPageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const {
    nodes,
    edges,
    stats,
    rawEdges,
    isLoading,
    isError,
    error,
    refetch,
    minimapColor,
  } = useKnowledgeGraph();

  const {
    selectedNode,
    searchQuery,
    activeFilters,
    connectedEdges,
    connectedNodes,
    styledNodes,
    visibleEdges,
    setSearchQuery,
    toggleFilter,
    resetFilters,
    onNodeClick,
    onPaneClick,
    highlightRelated,
    setSelectedNodeId,
  } = useGraphInteractions({ allNodes: nodes, allEdges: edges, rawEdges });

  const { fitView } = useReactFlow();

  // ── Context menu ───────────────────────────────────────────────
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    node: Node<KGNodeData>;
  } | null>(null);

  const handleContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      event.preventDefault();
      setContextMenu({
        x: event.clientX,
        y: event.clientY,
        node: node as Node<KGNodeData>,
      });
      setSelectedNodeId(node.id);
    },
    [setSelectedNodeId]
  );

  const handleCenterNode = useCallback(() => {
    if (contextMenu) {
      fitView({
        nodes: [{ id: contextMenu.node.id }],
        duration: 500,
        padding: 0.5,
      });
    }
  }, [contextMenu, fitView]);

  const handleCopyId = useCallback(() => {
    if (contextMenu) {
      navigator.clipboard.writeText(contextMenu.node.id).catch(() => {});
    }
  }, [contextMenu]);

  // ── Loading ────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <div className="h-[calc(100vh-220px)] overflow-hidden rounded-2xl border border-border bg-card shadow-enterprise">
          <GraphLoadingState />
        </div>
      </div>
    );
  }

  // ── Error ──────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <div className="h-[calc(100vh-220px)] overflow-hidden rounded-2xl border border-border bg-card shadow-enterprise">
          <GraphErrorState error={error} onRetry={() => refetch()} />
        </div>
      </div>
    );
  }

  // ── Empty ──────────────────────────────────────────────────────
  if (nodes.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <div className="h-[calc(100vh-220px)] overflow-hidden rounded-2xl border border-border bg-card shadow-enterprise">
          <GraphEmptyState
            onNavigateUpload={() => onNavigate?.("upload")}
          />
        </div>
      </div>
    );
  }

  // ── Graph ──────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <PageHeader />

      <div
        ref={containerRef}
        className="relative flex h-[calc(100vh-220px)] overflow-hidden rounded-2xl border border-border bg-card shadow-enterprise"
      >
        {/* Left sidebar */}
        <GraphSidebar
          stats={stats}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          activeFilters={activeFilters}
          onToggleFilter={toggleFilter}
          onResetFilters={resetFilters}
        />

        {/* Center canvas */}
        <div
          className="relative flex-1"
          onContextMenu={(e) => {
            // Only handle context menu on nodes (handled via node's onContextMenu)
          }}
        >
          <GraphToolbar
            onRefresh={() => refetch()}
            containerRef={containerRef}
          />
          <GraphCanvas
            nodes={styledNodes}
            edges={visibleEdges}
            onNodeClick={onNodeClick}
            onPaneClick={() => {
              onPaneClick();
              setContextMenu(null);
            }}
            onNodeDoubleClick={() => {}}
            minimapColor={minimapColor}
          />
        </div>

        {/* Right inspector */}
        {selectedNode && (
          <GraphInspector
            node={selectedNode}
            connectedNodes={connectedNodes}
            connectedEdges={connectedEdges}
            onClose={() => setSelectedNodeId(null)}
            onHighlightRelated={highlightRelated}
            onNavigate={onNavigate}
          />
        )}

        {/* Context menu */}
        <GraphContextMenu
          position={
            contextMenu ? { x: contextMenu.x, y: contextMenu.y } : null
          }
          nodeLabel={
            (contextMenu?.node.data as KGNodeData)?.label ?? ""
          }
          onClose={() => setContextMenu(null)}
          onCenterNode={handleCenterNode}
          onHighlightConnected={highlightRelated}
          onAskAI={() => onNavigate?.("assistant")}
          onCopyId={handleCopyId}
        />
      </div>
    </div>
  );
}

function PageHeader() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex flex-col justify-between gap-4 rounded-2xl border border-border bg-card/70 p-5 shadow-sm md:flex-row md:items-end md:p-6"
    >
      <div>
        <Badge variant="outline">
          <Share2 className="mr-1.5 h-3 w-3" />
          AI Knowledge Intelligence
        </Badge>
        <h1 className="mt-3 text-2xl font-semibold tracking-[-0.02em] md:text-3xl">
          Knowledge Graph
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
          Explore relationships between industrial documents, engineering
          concepts, equipment and AI-extracted knowledge.
        </p>
      </div>
    </motion.section>
  );
}
