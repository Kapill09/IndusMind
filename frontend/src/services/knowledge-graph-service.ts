import type { KGApiResponse } from "@/types/knowledge-graph";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

/**
 * Fetch the full knowledge graph from the backend.
 * Gracefully returns an empty graph if the backend is unreachable.
 */
export async function fetchKnowledgeGraph(): Promise<KGApiResponse> {
  const response = await fetch(`${API_BASE_URL}/knowledge-graph`);

  if (!response.ok) {
    const detail = await response
      .json()
      .then((body) => body?.detail)
      .catch(() => null);
    throw new Error(
      detail ?? `Knowledge graph request failed (${response.status})`
    );
  }

  const data: KGApiResponse = await response.json();

  return {
    nodes: Array.isArray(data?.nodes) ? data.nodes : [],
    edges: Array.isArray(data?.edges) ? data.edges : [],
  };
}
