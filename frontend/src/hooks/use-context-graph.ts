import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { type Node, type Edge, MarkerType } from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import type { ChatMessage } from "@/types";
import {
  fetchContextGraph,
  type ContextGraphNode,
  type ContextGraphEdge,
  type ContextGraphStats,
} from "@/services/context-graph-service";
import { MINIMAP_COLORS, NODE_WIDTH, NODE_HEIGHT } from "@/components/knowledge-graph/knowledge-graph-constants";
import type { KGNodeData } from "@/types/knowledge-graph";

const EMPTY_NODES: ContextGraphNode[] = [];
const EMPTY_EDGES: ContextGraphEdge[] = [];

/**
 * Apply Dagre hierarchical layout (top-to-bottom) to the graph nodes.
 * Uses the `rank` field from the backend as rank hints.
 */
function layoutWithDagre(
  rawNodes: ContextGraphNode[],
  rawEdges: ContextGraphEdge[],
): Node<KGNodeData>[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: "TB",
    nodesep: 60,
    ranksep: 100,
    edgesep: 30,
    marginx: 40,
    marginy: 40,
  });

  for (const node of rawNodes) {
    g.setNode(node.id, {
      width: NODE_WIDTH + 40,
      height: NODE_HEIGHT + 20,
      // Dagre doesn't natively support rank hints, but placing nodes by their
      // rank in a predictable order lets the algorithm produce a good layout.
    });
  }

  for (const edge of rawEdges) {
    // Only add edges where both endpoints exist.
    if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
      g.setEdge(edge.source, edge.target);
    }
  }

  dagre.layout(g);

  return rawNodes.map((node) => {
    const dagreNode = g.node(node.id);
    return {
      id: node.id,
      type: "kgNode",
      position: {
        x: (dagreNode?.x ?? 0) - (NODE_WIDTH + 40) / 2,
        y: (dagreNode?.y ?? 0) - (NODE_HEIGHT + 20) / 2,
      },
      data: {
        label: node.label,
        type: node.type,
        page: node.page,
        document: node.document ?? "",
        description: node.description,
        originalId: node.id,
      } satisfies KGNodeData,
      width: NODE_WIDTH + 40,
      height: NODE_HEIGHT + 20,
    };
  });
}

/**
 * Hook that fetches and lays out the Context Knowledge Graph for a specific
 * AI assistant message.
 */
export function useContextGraph(message: ChatMessage | null, userQuestion: string) {
  const question = userQuestion || message?.question || "";
  const sources = message?.sources ?? [];
  const entities = message?.entities ?? [];
  const answer = message?.content ?? "";
  const enabled = message != null && sources.length > 0 && question.length > 0;

  const query = useQuery({
    queryKey: [
      "context-graph",
      question,
      sources.map((s) => s.chunk_id).join(","),
    ],
    queryFn: () => fetchContextGraph(question, sources, entities, answer),
    enabled,
    staleTime: 5 * 60_000, // Cache for 5 minutes
    retry: 1,
  });

  const rawNodes = query.data?.nodes ?? EMPTY_NODES;
  const rawEdges = query.data?.edges ?? EMPTY_EDGES;
  const stats: ContextGraphStats = query.data?.stats ?? {
    totalNodes: 0,
    totalEdges: 0,
    entityTypes: {},
  };

  const flowNodes = useMemo(() => {
    if (rawNodes.length === 0) return [];
    return layoutWithDagre(rawNodes, rawEdges);
  }, [rawNodes, rawEdges]);

  const flowEdges: Edge[] = useMemo(() => {
    const nodeIds = new Set(rawNodes.map((n) => n.id));
    return rawEdges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e, i) => ({
        id: `ctx-edge-${i}`,
        source: e.source,
        target: e.target,
        type: "kgEdge",
        label: e.relationship,
        animated: e.weight >= 0.8,
        markerEnd: { type: MarkerType.ArrowClosed },
        data: { weight: e.weight, relationship: e.relationship },
      }));
  }, [rawNodes, rawEdges]);

  const minimapColor = (node: Node) => {
    const nt = (node.data as KGNodeData)?.type ?? "";
    return MINIMAP_COLORS[nt] ?? "#9ca3af";
  };

  return {
    nodes: flowNodes,
    edges: flowEdges,
    rawNodes,
    rawEdges,
    stats,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    minimapColor,
  };
}
