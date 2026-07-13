import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Maximize2,
  RotateCw,
  Search,
  Sparkles,
  X,
  ZoomIn,
  ZoomOut,
  TrendingUp,
} from "lucide-react";
import type { RagSource } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PDFViewer } from "@/components/pdf-viewer/pdf-viewer";

interface SourcePdfViewerDrawerProps {
  source: RagSource | null;
  sources?: RagSource[];
  confidenceScore?: number;
  onClose: () => void;
  onOpenKnowledgeGraph?: () => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
const PDF_VIEWER_BASE_URL = "https://mozilla.github.io/pdf.js/web/viewer.html";

function getBackendBaseUrl() {
  if (API_BASE_URL) return API_BASE_URL;
  if (typeof window === "undefined") return "http://127.0.0.1:8000";
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }
  return window.location.origin;
}

export function SourcePdfViewerDrawer({
  source,
  sources = [],
  confidenceScore,
  onClose,
  onOpenKnowledgeGraph,
}: SourcePdfViewerDrawerProps) {
  const [isCopied, setIsCopied] = useState(false);
  const [currentSourceIndex, setCurrentSourceIndex] = useState(0);

  const currentIndex = useMemo(() => {
    if (!source) return -1;
    return sources.findIndex((candidate) => candidate.chunk_id === source.chunk_id);
  }, [source, sources]);

  // Update current source index when source changes
  useEffect(() => {
    if (currentIndex >= 0) {
      setCurrentSourceIndex(currentIndex);
    }
  }, [currentIndex]);

  const currentSource = sources[currentSourceIndex] || source;
  const previousSource = currentSourceIndex > 0 ? sources[currentSourceIndex - 1] : null;
  const nextSource = currentSourceIndex >= 0 && currentSourceIndex < sources.length - 1 ? sources[currentSourceIndex + 1] : null;

  const pdfUrl = useMemo(() => {
    if (!currentSource) return "";
    const backendBaseUrl = getBackendBaseUrl();
    const documentId = currentSource.metadata?.document_id?.toString().trim();
    const filename = currentSource.metadata?.filename?.toString().trim();
    if (documentId) {
      return `${backendBaseUrl}/api/documents/${encodeURIComponent(documentId)}/pdf`;
    }

    const params = new URLSearchParams();
    if (filename) params.set("filename", filename);
    const basePath = `${backendBaseUrl}/documents/preview`;
    return params.toString() ? `${basePath}?${params.toString()}` : basePath;
  }, [currentSource]);

  const searchText = useMemo(() => {
    if (!currentSource) return "";
    return String(currentSource.text ?? currentSource.metadata?.heading ?? currentSource.metadata?.title ?? "").trim().replace(/\s+/g, " ");
  }, [currentSource]);

  const pageLabel = currentSource ? getPageLabel(currentSource) : "Page unknown";
  const title = currentSource?.metadata?.heading || currentSource?.metadata?.title || currentSource?.metadata?.filename || "Source document";
  const filename = currentSource?.metadata?.filename ?? "Uploaded document";
  const retrievalMode = getRetrievalMode(currentSource);
  const retrievalScore = currentSource?.score != null ? Math.round((currentSource.score ?? 0) * 100) : 0;
  const confidenceScoreLabel = confidenceScore != null ? `${confidenceScore}%` : `${Math.max(55, retrievalScore)}%`;
  const pageStart = currentSource?.page_start || 1;

  const handlePrevious = () => {
    if (currentSourceIndex > 0) {
      setCurrentSourceIndex(currentSourceIndex - 1);
    }
  };

  const handleNext = () => {
    if (currentSourceIndex < sources.length - 1) {
      setCurrentSourceIndex(currentSourceIndex + 1);
    }
  };

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && source) {
        onClose();
      }
    };

    if (source) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [source, onClose]);

  useEffect(() => {
    if (!source) {
      setIsCopied(false);
    }
  }, [source]);

  const handleCopyCitation = async () => {
    if (!currentSource) return;
    const citationText = [
      title,
      `${filename} • ${pageLabel}`,
      currentSource.text ? `Excerpt: ${currentSource.text}` : undefined,
      currentSource.metadata?.document_id ? `Document ID: ${currentSource.metadata.document_id}` : undefined,
    ]
      .filter(Boolean)
      .join("\n");

    try {
      await navigator.clipboard.writeText(citationText);
      setIsCopied(true);
      window.setTimeout(() => setIsCopied(false), 1800);
    } catch {
      // Graceful no-op for browsers without clipboard access.
    }
  };

  return (
    <AnimatePresence>
      {source && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[60] bg-background/80 backdrop-blur-sm"
            onClick={onClose}
          />

          <motion.div
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 24, stiffness: 220 }}
            className="fixed inset-y-0 right-0 z-[70] flex w-full max-w-7xl flex-col border-l border-border bg-card shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-label="Source inspection"
          >
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" aria-hidden="true" />
                  <h2 className="truncate text-base font-semibold text-foreground">{title}</h2>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {/* Page Badge */}
                  <div className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs">
                    <span className="font-medium text-muted-foreground">Page:</span>
                    <span className="font-semibold text-foreground">{pageLabel}</span>
                  </div>
                  
                  {/* Relevance Score */}
                  {retrievalScore > 0 && (
                    <div className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs">
                      <TrendingUp className="h-3 w-3 text-primary" />
                      <span className="font-medium text-muted-foreground">Relevance:</span>
                      <span className="font-semibold text-foreground">{retrievalScore}%</span>
                    </div>
                  )}
                  
                  {/* Confidence Score */}
                  {confidenceScore && (
                    <div className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs">
                      <span className="font-medium text-muted-foreground">Confidence:</span>
                      <span className="font-semibold text-foreground">{Math.round(confidenceScore)}%</span>
                    </div>
                  )}
                  
                  {/* Source Badge */}
                  <Badge variant="outline" className="animate-pulse border-primary/50 text-primary">
                    <Sparkles className="mr-1 h-3 w-3" aria-hidden="true" />
                    Source used by AI
                  </Badge>
                </div>
                
                {/* Highlighted Text Preview */}
                {searchText && (
                  <div className="mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                      Highlighted Text
                    </p>
                    <p className="line-clamp-2 text-sm leading-relaxed text-foreground">
                      {searchText.length > 200 ? searchText.substring(0, 200) + "..." : searchText}
                    </p>
                  </div>
                )}
              </div>
              
              <div className="flex items-center gap-2">
                {/* Navigation buttons for multiple sources */}
                {sources.length > 1 && (
                  <>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handlePrevious}
                      disabled={currentSourceIndex === 0}
                    >
                      <ChevronLeft className="mr-1 h-3.5 w-3.5" />
                      Previous
                    </Button>
                    <span className="text-xs font-medium text-muted-foreground">
                      {currentSourceIndex + 1} / {sources.length}
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleNext}
                      disabled={currentSourceIndex === sources.length - 1}
                    >
                      Next
                      <ChevronRight className="ml-1 h-3.5 w-3.5" />
                    </Button>
                    <div className="mx-2 h-6 w-px bg-border" />
                  </>
                )}
                
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCopyCitation}
                >
                  <Copy className="mr-2 h-3.5 w-3.5" />
                  {isCopied ? "Copied!" : "Copy Citation"}
                </Button>
                <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close source inspection">
                  <X className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </div>

            {/* PDF Viewer with highlighting */}
            <div className="flex-1 overflow-hidden">
              {pdfUrl ? (
                <PDFViewer
                  key={currentSource?.chunk_id}
                  pdfUrl={pdfUrl}
                  initialPage={pageStart}
                  highlightText={searchText}
                  onClose={onClose}
                />
              ) : (
                <div className="flex h-full items-center justify-center p-6 text-center">
                  <div>
                    <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
                    <p className="mt-4 text-sm font-medium text-foreground">PDF not available</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      The source document could not be loaded
                    </p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function getPageLabel(source: RagSource) {
  if (source.page_start && source.page_end) {
    return source.page_start === source.page_end ? `Page ${source.page_start}` : `Pages ${source.page_start}-${source.page_end}`;
  }
  if (source.page_start) return `Page ${source.page_start}`;
  if (source.page_end) return `Page ${source.page_end}`;
  return "Page unknown";
}

function getRetrievalMode(source: RagSource | null) {
  const metadata = source?.metadata ?? {};
  if (metadata.retrieval_method) return String(metadata.retrieval_method);
  if (metadata.structured) return "Structured";
  if (metadata.hybrid) return "Hybrid";
  if (source?.score && source.score >= 0.9) return "Semantic";
  return "Hybrid";
}
