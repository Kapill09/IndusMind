import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import type { Node, Edge } from "@xyflow/react";
import { fetchKnowledgeGraph } from "@/services/knowledge-graph-service";
import type { KGNode, KGStats } from "@/types/knowledge-graph";
import { MINIMAP_COLORS, NODE_WIDTH, NODE_HEIGHT } from "@/components/knowledge-graph/knowledge-graph-constants";

/** Data stored on every React Flow node. */
export interface KGNodeData extends Record<string, unknown> {
  label: string;
  nodeType: string;
  page: number | null;
  document: string;
  description: string;
  originalId: string;
}

/**
 * Simple force-directed positioning.
 * Positions nodes in a spiral layout grouped by type so they cluster visually.
 */
function layoutNodes(raw: KGNode[]): Node<KGNodeData>[] {
  const typeGroups: Record<string, KGNode[]> = {};
  for (const node of raw) {
    const t = node.type || "Unknown";
    (typeGroups[t] ??= []).push(node);
  }

  const nodes: Node<KGNodeData>[] = [];
  const types = Object.keys(typeGroups);
  const angleStep = (2 * Math.PI) / Math.max(types.length, 1);

  types.forEach((type, typeIndex) => {
    const group = typeGroups[type];
    const baseAngle = typeIndex * angleStep;
    const clusterRadius = 300 + types.length * 40;
    const cx = Math.cos(baseAngle) * clusterRadius;
    const cy = Math.sin(baseAngle) * clusterRadius;

    group.forEach((node, i) => {
      const innerAngle = (2 * Math.PI * i) / Math.max(group.length, 1);
      const innerRadius = 40 + group.length * 12;

      nodes.push({
        id: node.id,
        type: "kgNode",
        position: {
          x: cx + Math.cos(innerAngle) * innerRadius,
          y: cy + Math.sin(innerAngle) * innerRadius,
        },
        data: {
          label: node.label,
          nodeType: node.type,
          page: node.page,
          document: node.document,
          description: node.description,
          originalId: node.id,
        },
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
      });
    });
  });

  return nodes;
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

  const flowNodes = useMemo(() => layoutNodes(rawNodes), [rawNodes]);

  const flowEdges: Edge[] = useMemo(() => {
    const nodeIds = new Set(rawNodes.map((n) => n.id));
    return rawEdges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e, i) => ({
        id: `edge-${i}`,
        source: e.source,
        target: e.target,
        type: "kgEdge",
        data: { relationship: e.relationship, weight: e.weight },
        animated: e.weight >= 0.8,
      }));
  }, [rawNodes, rawEdges]);

  const stats = useMemo(
    () => computeStats(rawNodes, rawEdges.length),
    [rawNodes, rawEdges]
  );

  const minimapColor = (node: Node) => {
    const nt = (node.data as KGNodeData)?.nodeType ?? "";
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
