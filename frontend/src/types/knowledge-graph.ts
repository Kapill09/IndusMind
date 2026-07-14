/** Types returned by GET /knowledge-graph */

export interface KGNode {
  id: string;
  label: string;
  type: string;
  page: number | null;
  document: string;
  description: string;
}

/** Data stored on every React Flow node. */
export interface KGNodeData extends Record<string, unknown> {
  label: string;
  type: string;
  page: number | null;
  document: string;
  description: string;
  originalId: string;
}

export interface KGEdge {
  source: string;
  target: string;
  relationship: string;
  weight: number;
}

export interface KGApiResponse {
  nodes: KGNode[];
  edges: KGEdge[];
}

/** All recognised entity types from the backend service. */
export type KGNodeType =
  | "Question"
  | "Document"
  | "Equipment"
  | "Problem Statements"
  | "Technologies"
  | "Safety terms"
  | "Standards"
  | "Regulations"
  | "Maintenance concepts"
  | "SOPs"
  | "Page"
  | "Chunk";

/** Filter categories exposed in the sidebar. */
export type KGFilterKey =
  | "Document"
  | "Equipment"
  | "Technology"
  | "Safety"
  | "Maintenance"
  | "Problem Statement"
  | "Standards"
  | "Regulations";

/** Maps a filter key to the backend node types it covers. */
export const FILTER_TO_NODE_TYPES: Record<KGFilterKey, string[]> = {
  Document: ["Document"],
  Equipment: ["Equipment"],
  Technology: ["Technologies"],
  Safety: ["Safety terms"],
  Maintenance: ["Maintenance concepts"],
  "Problem Statement": ["Problem Statements"],
  Standards: ["Standards"],
  Regulations: ["Regulations"],
};

/** Computed statistics from the graph data. */
export interface KGStats {
  documents: number;
  problemStatements: number;
  equipment: number;
  technologies: number;
  maintenance: number;
  safety: number;
  standards: number;
  regulations: number;
  totalNodes: number;
  totalEdges: number;
}

/** Color configuration for a single node type. */
export interface NodeColorConfig {
  bg: string;
  bgDark: string;
  border: string;
  borderDark: string;
  text: string;
  textDark: string;
  glow: string;
}
