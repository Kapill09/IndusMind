import { useEffect, useMemo, useState } from "react";
import type { KnowledgeDocument, UploadResponse } from "@/types";

const STORAGE_KEY = "indus-mind-documents";

export function useLocalDocuments() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];

    try {
      const parsed = JSON.parse(stored) as KnowledgeDocument[];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(documents));
  }, [documents]);

  const addUploadedDocument = (response: UploadResponse) => {
    const summary = response.ingestion;
    const document: KnowledgeDocument = {
      id: `${summary.filename}-${Date.now()}`,
      filename: summary.filename,
      pages: summary.pages,
      chunks: summary.chunks,
      vectors: summary.vectors,
      uploadedAt: new Date().toISOString(),
      status: summary.success ? "indexed" : "failed",
    };

    setDocuments((current) => [document, ...current.filter((item) => item.filename !== document.filename)]);
  };

  const totals = useMemo(
    () => ({
      documents: documents.length,
      pages: documents.reduce((sum, document) => sum + document.pages, 0),
      chunks: documents.reduce((sum, document) => sum + document.chunks, 0),
      vectors: documents.reduce((sum, document) => sum + document.vectors, 0),
    }),
    [documents],
  );

  return { documents, totals, addUploadedDocument };
}
