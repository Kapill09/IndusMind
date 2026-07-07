import React from "react";
import {
  BaseEdge,
  type EdgeProps,
  getBezierPath,
} from "@xyflow/react";

/**
 * Custom animated edge with bezier path and subtle animation.
 */
function GraphEdgeInner({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
}: EdgeProps) {
  const weight = (data as { weight?: number })?.weight ?? 0.5;
  const relationship = (data as { relationship?: string })?.relationship ?? "";

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const opacity = Math.max(0.15, Math.min(weight, 0.7));
  const strokeWidth = weight >= 0.8 ? 1.5 : 1;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: "hsl(var(--muted-foreground))",
          strokeWidth,
          opacity,
        }}
      />
      {relationship && weight >= 0.7 && (
        <text
          x={labelX}
          y={labelY}
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-muted-foreground text-[8px] pointer-events-none select-none"
          style={{ opacity: 0.5 }}
        >
          {relationship}
        </text>
      )}
    </>
  );
}

export const GraphEdge = React.memo(GraphEdgeInner);
