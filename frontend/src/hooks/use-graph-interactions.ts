import { useCallback, useMemo, useState } from "react";
import type { Node, Edge } from "@xyflow/react";
import { FILTER_TO_NODE_TYPES, type KGFilterKey } from "@/types/knowledge-graph";
import type { KGNodeData } from "@/types/knowledge-graph";

interface UseGraphInteractionsOptions {
  allNodes: Node<KGNodeData>[];
  allEdges: Edge[];
  rawEdges: { source: string; target: string; relationship: string; weight: number }[];
}

export function useGraphInteractions({
  allNodes,
  allEdges,
  rawEdges,
}: UseGraphInteractionsOptions) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilters, setActiveFilters] = useState<Set<KGFilterKey>>(new Set());
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set());

  // ── Selected node ──────────────────────────────────────────────
  const selectedNode = useMemo(
    () => allNodes.find((n) => n.id === selectedNodeId) ?? null,
    [allNodes, selectedNodeId]
  );

  // ── Connections for the selected node ──────────────────────────
  const connectedEdges = useMemo(() => {
    if (!selectedNodeId) return [];
    return rawEdges.filter(
      (e) => e.source === selectedNodeId || e.target === selectedNodeId
    );
  }, [rawEdges, selectedNodeId]);

  const connectedNodeIds = useMemo(() => {
    const ids = new Set<string>();
    for (const e of connectedEdges) {
      ids.add(e.source);
      ids.add(e.target);
    }
    ids.delete(selectedNodeId ?? "");
    return ids;
  }, [connectedEdges, selectedNodeId]);

  const connectedNodes = useMemo(
    () => allNodes.filter((n) => connectedNodeIds.has(n.id)),
    [allNodes, connectedNodeIds]
  );

  // ── Search ─────────────────────────────────────────────────────
  const searchMatchIds = useMemo(() => {
    if (!searchQuery.trim()) return new Set<string>();
    const q = searchQuery.toLowerCase();
    return new Set(
      allNodes
        .filter(
          (n) =>
            (n.data as KGNodeData).label.toLowerCase().includes(q) ||
            (n.data as KGNodeData).description.toLowerCase().includes(q)
        )
        .map((n) => n.id)
    );
  }, [allNodes, searchQuery]);

  // ── Filters ────────────────────────────────────────────────────
  const toggleFilter = useCallback((key: KGFilterKey) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const resetFilters = useCallback(() => {
    setActiveFilters(new Set());
    setSearchQuery("");
    setHighlightedNodes(new Set());
    setSelectedNodeId(null);
  }, []);

  // ── Filtered nodes & edges ─────────────────────────────────────
  const activeTypeSet = useMemo(() => {
    if (activeFilters.size === 0) return null;
    const types = new Set<string>();
    for (const key of activeFilters) {
      for (const t of FILTER_TO_NODE_TYPES[key] ?? []) types.add(t);
    }
    return types;
  }, [activeFilters]);

  const visibleNodes = useMemo(() => {
    let result = allNodes;

    if (activeTypeSet) {
      result = result.filter((n) =>
        activeTypeSet.has((n.data as KGNodeData).type)
      );
    }

    if (searchQuery.trim()) {
      result = result.filter((n) => searchMatchIds.has(n.id));
    }

    return result;
  }, [allNodes, activeTypeSet, searchQuery, searchMatchIds]);

  const visibleNodeIds = useMemo(
    () => new Set(visibleNodes.map((n) => n.id)),
    [visibleNodes]
  );

  const visibleEdges = useMemo(
    () =>
      allEdges.filter(
        (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
      ),
    [allEdges, visibleNodeIds]
  );

  // ── Styled nodes (glow, fade, highlight) ───────────────────────
  const styledNodes = useMemo(() => {
    const hasSelection = selectedNodeId != null;
    const hasHighlight = highlightedNodes.size > 0;

    return visibleNodes.map((n) => {
      const isSelected = n.id === selectedNodeId;
      const isConnected = connectedNodeIds.has(n.id);
      const isHighlighted = highlightedNodes.has(n.id);
      const isSearchMatch = searchMatchIds.size > 0 && searchMatchIds.has(n.id);

      let opacity = 1;
      if (hasSelection && !isSelected && !isConnected) opacity = 0.25;
      if (hasHighlight && !isHighlighted && !isSelected) opacity = 0.2;

      return {
        ...n,
        data: {
          ...n.data,
          _isSelected: isSelected,
          _isConnected: isConnected,
          _isHighlighted: isHighlighted,
          _isSearchMatch: isSearchMatch,
          _opacity: opacity,
        },
      };
    });
  }, [
    visibleNodes,
    selectedNodeId,
    connectedNodeIds,
    highlightedNodes,
    searchMatchIds,
  ]);

  // ── Handlers ───────────────────────────────────────────────────
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNodeId(node.id);
      setHighlightedNodes(new Set());
    },
    []
  );

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setHighlightedNodes(new Set());
  }, []);

  const highlightRelated = useCallback(() => {
    if (!selectedNodeId) return;
    const ids = new Set(connectedNodeIds);
    ids.add(selectedNodeId);
    setHighlightedNodes(ids);
  }, [selectedNodeId, connectedNodeIds]);

  return {
    // State
    selectedNode,
    selectedNodeId,
    searchQuery,
    activeFilters,
    highlightedNodes,

    // Derived
    connectedEdges,
    connectedNodes,
    searchMatchIds,
    styledNodes,
    visibleEdges,
    visibleNodes,

    // Handlers
    setSearchQuery,
    toggleFilter,
    resetFilters,
    setSelectedNodeId,
    onNodeClick,
    onPaneClick,
    highlightRelated,
  };
}
