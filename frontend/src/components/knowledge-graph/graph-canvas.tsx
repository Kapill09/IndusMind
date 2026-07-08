import { useEffect, useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  useReactFlow,
  type Node,
  type Edge,
  type NodeTypes,
  type EdgeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { GraphNode } from "@/components/knowledge-graph/graph-node";
import { GraphEdge } from "@/components/knowledge-graph/graph-edge";

interface GraphCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodeClick: (event: React.MouseEvent, node: Node) => void;
  onPaneClick: () => void;
  onNodeDoubleClick?: (event: React.MouseEvent, node: Node) => void;
  minimapColor: (node: Node) => string;
}

const nodeTypes: NodeTypes = { kgNode: GraphNode };
const edgeTypes: EdgeTypes = { kgEdge: GraphEdge };

export function GraphCanvas({
  nodes,
  edges,
  onNodeClick,
  onPaneClick,
  onNodeDoubleClick,
  minimapColor,
}: GraphCanvasProps) {
  const { fitView } = useReactFlow();

  const handleNodeDoubleClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      onNodeDoubleClick?.(event, node);
      fitView({ nodes: [{ id: node.id }], duration: 400, padding: 0.5 });
    },
    [fitView, onNodeDoubleClick]
  );

  console.log("[GraphCanvas] Rendering with nodes:", nodes?.length, "edges:", edges?.length);

  useEffect(() => {
    if (nodes.length === 0) {
      return;
    }

    window.requestAnimationFrame(() => {
      fitView({ duration: 600, padding: 0.3 });
    });
  }, [edges.length, fitView, nodes.length]);

  const defaultEdgeOptions = useMemo(
    () => ({
      type: "kgEdge" as const,
    }),
    []
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodeClick={onNodeClick}
      onPaneClick={onPaneClick}
      onNodeDoubleClick={handleNodeDoubleClick}
      defaultEdgeOptions={defaultEdgeOptions}
      fitView
      fitViewOptions={{ padding: 0.3, duration: 600 }}
      minZoom={0.1}
      maxZoom={2.5}
      proOptions={{ hideAttribution: true }}
      className="bg-background"
      deleteKeyCode={null}
      selectionKeyCode={null}
      multiSelectionKeyCode={null}
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={20}
        size={1}
        className="!bg-background"
        color="hsl(var(--muted-foreground) / 0.15)"
      />
      <Controls
        showInteractive={false}
        className="!rounded-xl !border !border-border !bg-card !shadow-sm [&>button]:!border-border [&>button]:!bg-card [&>button]:!text-foreground hover:[&>button]:!bg-muted"
      />
      <MiniMap
        nodeColor={minimapColor}
        maskColor="hsl(var(--background) / 0.85)"
        className="!rounded-xl !border !border-border !bg-card !shadow-sm"
        pannable
        zoomable
      />
    </ReactFlow>
  );
}
