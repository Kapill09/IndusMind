import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { type Node, type Edge, MarkerType } from "@xyflow/react";
import { fetchKnowledgeGraph } from "@/services/knowledge-graph-service";
import type { KGEdge, KGNode, KGStats } from "@/types/knowledge-graph";
import { MINIMAP_COLORS, NODE_WIDTH, NODE_HEIGHT } from "@/components/knowledge-graph/knowledge-graph-constants";

export type KGDisplayMode = "summary" | "full";

const SUMMARY_NODE_LIMIT = 25;
const SUMMARY_EDGE_LIMIT = 35;
const EMPTY_KG_NODES: KGNode[] = [];
const EMPTY_KG_EDGES: KGEdge[] = [];
const DETAIL_NODE_TYPES = new Set(["Page", "Chunk"]);
const MAIN_TYPE_QUOTAS: Record<string, number> = {
  Document: 3,
  Equipment: 5,
  "Problem Statements": 3,
  Technologies: 4,
  "Maintenance concepts": 3,
  "Safety terms": 3,
  Standards: 2,
  Regulations: 2,
  SOPs: 2,
};

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

function summarizeGraph(rawNodes: KGNode[], rawEdges: KGEdge[]) {
  if (rawNodes.length <= SUMMARY_NODE_LIMIT) {
    return { nodes: rawNodes, edges: rawEdges };
  }

  const nodeById = new Map(rawNodes.map((node) => [node.id, node]));
  const scores = new Map<string, number>();

  for (const edge of rawEdges) {
    const weight = Number.isFinite(edge.weight) ? edge.weight : 0.5;
    scores.set(edge.source, (scores.get(edge.source) ?? 0) + weight);
    scores.set(edge.target, (scores.get(edge.target) ?? 0) + weight);
  }

  const scoreNode = (node: KGNode) => scores.get(node.id) ?? 0;
  const mainNodes = rawNodes.filter((node) => !DETAIL_NODE_TYPES.has(node.type));
  const candidates = mainNodes.length > 0 ? mainNodes : rawNodes;
  const selectedIds = new Set<string>();

  for (const [type, quota] of Object.entries(MAIN_TYPE_QUOTAS)) {
    candidates
      .filter((node) => node.type === type)
      .sort((a, b) => scoreNode(b) - scoreNode(a) || a.label.localeCompare(b.label))
      .slice(0, quota)
      .forEach((node) => selectedIds.add(node.id));
  }

  candidates
    .filter((node) => !selectedIds.has(node.id))
    .sort((a, b) => scoreNode(b) - scoreNode(a) || a.label.localeCompare(b.label))
    .slice(0, Math.max(SUMMARY_NODE_LIMIT - selectedIds.size, 0))
    .forEach((node) => selectedIds.add(node.id));

  const selectedNodes = Array.from(selectedIds)
    .map((id) => nodeById.get(id))
    .filter((node): node is KGNode => Boolean(node))
    .sort((a, b) => {
      const typeRank =
        Object.keys(MAIN_TYPE_QUOTAS).indexOf(a.type) -
        Object.keys(MAIN_TYPE_QUOTAS).indexOf(b.type);
      return typeRank || scoreNode(b) - scoreNode(a) || a.label.localeCompare(b.label);
    });

  const selectedEdges = rawEdges
    .filter((edge) => selectedIds.has(edge.source) && selectedIds.has(edge.target))
    .sort((a, b) => {
      const aWeight = Number.isFinite(a.weight) ? a.weight : 0;
      const bWeight = Number.isFinite(b.weight) ? b.weight : 0;
      const aEndpointScore = (scores.get(a.source) ?? 0) + (scores.get(a.target) ?? 0);
      const bEndpointScore = (scores.get(b.source) ?? 0) + (scores.get(b.target) ?? 0);
      return bWeight - aWeight || bEndpointScore - aEndpointScore;
    })
    .slice(0, SUMMARY_EDGE_LIMIT);

  return { nodes: selectedNodes, edges: selectedEdges };
}

export function useKnowledgeGraph(displayMode: KGDisplayMode = "summary", documentIds?: string[] | null) {
  const query = useQuery({
    queryKey: ["knowledge-graph", { documentIds }],
    queryFn: () => fetchKnowledgeGraph(documentIds ?? null),
    staleTime: 60_000,
    retry: 2,
  });

  const rawNodes = query.data?.nodes ?? EMPTY_KG_NODES;
  const rawEdges = query.data?.edges ?? EMPTY_KG_EDGES;
  const graphData = useMemo(() => {
    if (displayMode === "full") {
      return { nodes: rawNodes, edges: rawEdges };
    }

    return summarizeGraph(rawNodes, rawEdges);
  }, [displayMode, rawNodes, rawEdges]);

  const displayNodes = graphData.nodes;
  const displayEdges = graphData.edges;

  const flowNodes = useMemo(() => {
    return layoutNodes(displayNodes);
  }, [displayNodes]);

  const flowEdges: Edge[] = useMemo(() => {
    const nodeIds = new Set(displayNodes.map((n) => n.id));
    const edges = displayEdges
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
    return edges;
  }, [displayNodes, displayEdges]);

  const stats = useMemo(
    () => computeStats(displayNodes, displayEdges.length),
    [displayNodes, displayEdges]
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
    displayRawNodes: displayNodes,
    displayRawEdges: displayEdges,
    displayMode,
    isSummarized: displayMode === "summary" && rawNodes.length > displayNodes.length,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    minimapColor,
  };
}
