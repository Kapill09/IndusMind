export type PageKey = "dashboard" | "assistant" | "upload" | "documents" | "analytics" | "settings" | "knowledge-graph";

export interface UploadSummary {
  filename: string;
  pages: number;
  chunks: number;
  vectors: number;
  collection: string;
  success: boolean;
}

export interface UploadResponse {
  success: boolean;
  filename: string;
  file_size: number;
  ingestion: UploadSummary;
}

export interface RagSource {
  chunk_id: string;
  text?: string;
  page_start: number | null;
  page_end: number | null;
  score: number | null;
  metadata: {
    filename?: string;
    document_id?: string;
    page_start?: number;
    page_end?: number;
    heading?: string;
    title?: string;
    combined_score?: number;
    [key: string]: unknown;
  };
}

export interface AskResponse {
  success: boolean;
  question: string;
  answer: string;
  model: string;
  retrieval_time_ms: number;
  total_results: number;
  sources: RagSource[];
  entities?: Array<{ label: string; type: string }>;
  context_chunks?: number;
  retrieval_scope?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: Date;
  sources?: RagSource[];
  confidence?: number;
  latencyMs?: number;
  model?: string;
  entities?: Array<{ label: string; type: string }>;
  contextChunks?: number;
  retrievalScope?: string;
}

export interface KnowledgeDocument {
  /** Canonical document identifier from ChromaDB metadata. */
  document_id: string;
  /** Alias kept for backward compatibility — set equal to document_id. */
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  vectors: number;
  uploadedAt: string;
  status: "indexed" | "processing" | "failed";
}
