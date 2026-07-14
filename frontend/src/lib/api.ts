import type { AskResponse, KnowledgeDocument, UploadResponse } from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
const INVALID_DOCUMENT_ID_PLACEHOLDERS = new Set(["string", "null", "undefined"]);

function sanitizeDocumentIds(documentIds?: string[] | null): string[] | undefined {
  if (!Array.isArray(documentIds)) {
    return undefined;
  }

  const cleanedIds = documentIds
    .map((documentId) => (typeof documentId === "string" ? documentId.trim() : ""))
    .filter((documentId) => documentId.length > 0)
    .filter((documentId) => !INVALID_DOCUMENT_ID_PLACEHOLDERS.has(documentId.toLowerCase()))
    .filter((documentId, index, values) => values.indexOf(documentId) === index);

  return cleanedIds.length > 0 ? cleanedIds : undefined;
}

function buildAskBody(question: string, topK: number, documentIds?: string[] | null) {
  const body: Record<string, unknown> = { question, top_k: topK };
  const sanitizedDocumentIds = sanitizeDocumentIds(documentIds);

  if (sanitizedDocumentIds && sanitizedDocumentIds.length > 0) {
    body.document_ids = sanitizedDocumentIds;
  }

  return body;
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      typeof payload?.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

export async function askQuestion(
  question: string,
  topK = 5,
  documentIds?: string[] | null,
): Promise<AskResponse> {
  const body = buildAskBody(question, topK, documentIds);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Unable to reach the assistant API. Check that the backend server is running.");
  }

  return parseJsonResponse<AskResponse>(response);
}

export function uploadDocument(
  file: File,
  onProgress: (progress: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    request.onload = () => {
      try {
        const payload = JSON.parse(request.responseText || "{}");
        if (request.status >= 200 && request.status < 300) {
          onProgress(100);
          resolve(payload as UploadResponse);
          return;
        }
        reject(new Error(payload?.detail ?? `Upload failed with status ${request.status}`));
      } catch (error) {
        reject(error);
      }
    };

    request.onerror = () => reject(new Error("Upload failed. Check the API server and network."));
    request.open("POST", `${API_BASE_URL}/upload`);
    request.send(formData);
  });
}

export async function fetchDocuments(): Promise<KnowledgeDocument[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/documents`);
  } catch {
    throw new Error("Unable to reach the documents API. Check that the backend server is running.");
  }

  const payload = await parseJsonResponse<Record<string, unknown>[]>(response);
  if (!Array.isArray(payload)) return [];

  return payload.map((doc) => ({
    document_id: String(doc.document_id ?? ""),
    id: String(doc.document_id ?? ""),
    filename: String(doc.filename ?? "unknown.pdf"),
    pages: Number(doc.pages ?? 0),
    chunks: Number(doc.chunks ?? 0),
    vectors: Number(doc.chunks ?? 0),
    uploadedAt: String(doc.uploaded_at ?? new Date().toISOString()),
    status: (doc.status as KnowledgeDocument["status"]) ?? "indexed",
  }));
}

export async function fetchKnowledgeGraph(): Promise<{ nodes: any[]; edges: any[] }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/knowledge-graph`);
  } catch {
    throw new Error("Unable to reach the knowledge graph API.");
  }
  return parseJsonResponse<{ nodes: any[]; edges: any[] }>(response);
}
