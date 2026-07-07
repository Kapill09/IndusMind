import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { type Node, type Edge, MarkerType } from "@xyflow/react";
import { fetchKnowledgeGraph } from "@/services/knowledge-graph-service";
import type { KGNode, KGStats } from "@/types/knowledge-graph";
import { MINIMAP_COLORS, NODE_WIDTH, NODE_HEIGHT } from "@/components/knowledge-graph/knowledge-graph-constants";

/** Data stored on every React Flow node. */
export interface KGNodeData extends Record<string, unknown> {
  label: string;
  type: string;
  page: number | null;
  document: string;
  description: string;
  originalId: string;
}

/**
 * Simple grid positioning for React Flow nodes.
 */
function layoutNodes(raw: KGNode[]): Node<KGNodeData>[] {
  const COLUMNS = Math.max(Math.ceil(Math.sqrt(raw.length)), 1);
  const X_SPACING = 250;
  const Y_SPACING = 150;

  return raw.map((node, index) => {
    const row = Math.floor(index / COLUMNS);
    const col = index % COLUMNS;
    
    return {
      id: node.id,
      type: "kgNode",
      position: {
        x: col * X_SPACING,
        y: row * Y_SPACING,
      },
      data: {
        label: node.label,
        type: node.type,
        page: node.page,
        document: node.document,
        description: node.description,
        originalId: node.id,
      },
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    };
  });
}

function computeStats(raw: KGNode[], edgeCount: number): KGStats {
  const counts: Record<string, number> = {};
  for (const node of raw) {
    counts[node.type] = (counts[node.type] || 0) + 1;
  }

  return {
    documents: counts["Document"] || 0,
    problemStatements: counts["Problem Statements"] || 0,
    equipment: counts["Equipment"] || 0,
    technologies: counts["Technologies"] || 0,
    maintenance: counts["Maintenance concepts"] || 0,
    safety: counts["Safety terms"] || 0,
    standards: counts["Standards"] || 0,
    regulations: counts["Regulations"] || 0,
    totalNodes: raw.length,
    totalEdges: edgeCount,
  };
}

export function useKnowledgeGraph() {
  const query = useQuery({
    queryKey: ["knowledge-graph"],
    queryFn: fetchKnowledgeGraph,
    staleTime: 60_000,
    retry: 2,
  });

  const rawNodes = query.data?.nodes ?? [];
  const rawEdges = query.data?.edges ?? [];

  const flowNodes = useMemo(() => {
    const nodes = layoutNodes(rawNodes);
    console.log("number of nodes:", nodes.length);
    return nodes;
  }, [rawNodes]);

  const flowEdges: Edge[] = useMemo(() => {
    const nodeIds = new Set(rawNodes.map((n) => n.id));
    const edges = rawEdges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e, i) => ({
        id: `edge-${i}`,
        source: e.source,
        target: e.target,
        type: "kgEdge",
        label: e.relationship,
        animated: e.weight >= 0.8,
        markerEnd: { type: MarkerType.ArrowClosed },
        data: { weight: e.weight, relationship: e.relationship },
      }));
    console.log("number of edges:", edges.length);
    return edges;
  }, [rawNodes, rawEdges]);

  const stats = useMemo(
    () => computeStats(rawNodes, rawEdges.length),
    [rawNodes, rawEdges]
  );

  const minimapColor = (node: Node) => {
    const nt = (node.data as KGNodeData)?.type ?? "";
    return MINIMAP_COLORS[nt] ?? "#9ca3af";
  };

  return {
    nodes: flowNodes,
    edges: flowEdges,
    stats,
    rawNodes,
    rawEdges,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    minimapColor,
  };
}
