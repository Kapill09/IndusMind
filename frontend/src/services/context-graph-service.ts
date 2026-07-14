import type { RagSource } from "@/types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
const REQUEST_TIMEOUT_MS = 30_000;

export interface ContextGraphNode {
  id: string;
  label: string;
  type: string;
  description: string;
  rank: number;
  confidence: number | null;
  page: number | null;
  document: string | null;
  sourceChunkId: string | null;
}

export interface ContextGraphEdge {
  source: string;
  target: string;
  relationship: string;
  weight: number;
}

export interface ContextGraphStats {
  totalNodes: number;
  totalEdges: number;
  entityTypes: Record<string, number>;
}

export interface ContextGraphResponse {
  nodes: ContextGraphNode[];
  edges: ContextGraphEdge[];
  stats: ContextGraphStats;
}

/**
 * Build an answer-scoped context graph from the RAG response data.
 * Calls POST /api/context-graph — does NOT query ChromaDB again.
 */
export async function fetchContextGraph(
  question: string,
  sources: RagSource[],
  entities: Array<{ label: string; type: string }>,
  answer: string,
): Promise<ContextGraphResponse> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/api/context-graph`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      signal: controller.signal,
      body: JSON.stringify({ question, sources, entities, answer }),
    });

    if (!response.ok) {
      let detail: string | null = null;
      try {
        const body = await response.json();
        detail = body?.detail;
      } catch {
        // ignore parse errors
      }
      throw new Error(detail ?? `Context graph request failed (${response.status})`);
    }

    const data: ContextGraphResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Context graph request timed out.");
    }
    throw err;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
