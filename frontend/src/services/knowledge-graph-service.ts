import type { KGApiResponse } from "@/types/knowledge-graph";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 30_000;

/**
 * Fetch the full knowledge graph from the backend.
 * Gracefully returns an empty graph if the backend is unreachable.
 */
export async function fetchKnowledgeGraph(documentIds?: string[] | null): Promise<KGApiResponse> {
  const params = documentIds && documentIds.length ? `?${documentIds.map((id) => `document_ids=${encodeURIComponent(id)}`).join("&")}` : "";
  const url = `${API_BASE_URL}/knowledge-graph${params}`;
  console.log("[fetchKnowledgeGraph] Request URL:", url);
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => {
    controller.abort();
  }, REQUEST_TIMEOUT_MS);
  
  try {
    const response = await fetch(url, {
      method: "GET",
      signal: controller.signal,
      headers: {
        "Accept": "application/json",
      },
    });

    console.log("[fetchKnowledgeGraph] Status:", response.status);

    if (!response.ok) {
      let detail = null;
      try {
        const body = await response.json();
        detail = body?.detail;
      } catch (e) {
        console.warn("[fetchKnowledgeGraph] Could not parse error body", e);
      }
      throw new Error(detail ?? `Knowledge graph request failed (${response.status})`);
    }

    const data = await response.json().catch((error) => {
      console.error("[fetchKnowledgeGraph] Response JSON parse error:", error);
      throw new Error("Knowledge graph response was not valid JSON.");
    });
    console.log("[fetchKnowledgeGraph] Response JSON:", data);

    // Handle multiple backend shapes flexibly
    let nodes = [];
    let edges = [];

    if (Array.isArray(data?.nodes)) {
      nodes = data.nodes;
    } else if (Array.isArray(data?.documents)) {
      nodes = data.documents;
    } else if (Array.isArray(data?.graph?.nodes)) {
      nodes = data.graph.nodes;
    } else if (Array.isArray(data?.data?.nodes)) {
      nodes = data.data.nodes;
    }

    if (Array.isArray(data?.edges)) {
      edges = data.edges;
    } else if (Array.isArray(data?.relationships)) {
      edges = data.relationships;
    } else if (Array.isArray(data?.graph?.edges)) {
      edges = data.graph.edges;
    } else if (Array.isArray(data?.data?.edges)) {
      edges = data.data.edges;
    }

    console.log("[fetchKnowledgeGraph] Parsed graph:", {
      nodes: nodes.length,
      edges: edges.length,
    });
    return { nodes, edges };
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      console.error("[fetchKnowledgeGraph] Request timed out:", url);
      throw new Error("Knowledge graph request timed out.");
    }
    console.error("[fetchKnowledgeGraph] error:", err);
    throw err;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
