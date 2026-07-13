import { useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchDocuments } from "@/lib/api";
import type { KnowledgeDocument } from "@/types";

/** Shared React Query key used by all document consumers. */
export const DOCUMENTS_QUERY_KEY = ["documents"] as const;

/**
 * Single source of truth for the document inventory.
 *
 * Replaces the previous localStorage-backed hook. Every component that calls
 * this hook shares the same React Query cache entry, so uploading a document
 * on the Upload page and invalidating the cache automatically refreshes the
 * Documents page, Sources popup, Dashboard, and Knowledge Graph.
 */
export function useLocalDocuments() {
  const queryClient = useQueryClient();

  const { data: documents = [], isLoading, isError } = useQuery<KnowledgeDocument[]>({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: fetchDocuments,
    staleTime: 15_000,
    refetchOnWindowFocus: true,
  });

  /**
   * Call after a successful upload to refresh the document list everywhere.
   * This replaces the old `addUploadedDocument` callback.
   */
  const refreshDocuments = () => {
    queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
  };

  const totals = useMemo(
    () => ({
      documents: documents.length,
      pages: documents.reduce((sum, doc) => sum + doc.pages, 0),
      chunks: documents.reduce((sum, doc) => sum + doc.chunks, 0),
      vectors: documents.reduce((sum, doc) => sum + doc.vectors, 0),
    }),
    [documents],
  );

  return { documents, totals, refreshDocuments, isLoading, isError };
}
