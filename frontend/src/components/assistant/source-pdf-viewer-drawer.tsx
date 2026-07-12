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
} from "lucide-react";
import type { RagSource } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

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
  const [iframeError, setIframeError] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const currentIndex = useMemo(() => {
    if (!source) return -1;
    return sources.findIndex((candidate) => candidate.chunk_id === source.chunk_id);
  }, [source, sources]);

  const previousSource = currentIndex > 0 ? sources[currentIndex - 1] : null;
  const nextSource = currentIndex >= 0 && currentIndex < sources.length - 1 ? sources[currentIndex + 1] : null;

  const pdfUrl = useMemo(() => {
    if (!source) return "";
    const backendBaseUrl = getBackendBaseUrl();
    const documentId = source.metadata?.document_id?.toString().trim();
    const filename = source.metadata?.filename?.toString().trim();
    if (documentId) {
      return `${backendBaseUrl}/api/documents/${encodeURIComponent(documentId)}/pdf`;
    }

    const params = new URLSearchParams();
    if (filename) params.set("filename", filename);
    const basePath = `${backendBaseUrl}/documents/preview`;
    return params.toString() ? `${basePath}?${params.toString()}` : basePath;
  }, [source]);

  const searchText = useMemo(() => {
    if (!source) return "";
    return String(source.text ?? source.metadata?.heading ?? source.metadata?.title ?? "").trim().replace(/\s+/g, " ").slice(0, 180);
  }, [source]);

  const pageLabel = source ? getPageLabel(source) : "Page unknown";
  const title = source?.metadata?.heading || source?.metadata?.title || source?.metadata?.filename || "Source document";
  const filename = source?.metadata?.filename ?? "Uploaded document";
  const retrievalMode = getRetrievalMode(source);
  const retrievalScore = source?.score != null ? Math.round((source.score ?? 0) * 100) : 0;
  const confidenceScoreLabel = confidenceScore != null ? `${confidenceScore}%` : `${Math.max(55, retrievalScore)}%`;

  const viewerUrl = useMemo(() => {
    if (!pdfUrl) return "";
    const pageNumber = source?.page_start ?? source?.metadata?.page_start ?? 1;
    const params = new URLSearchParams({
      file: pdfUrl,
      page: String(pageNumber),
      zoom: "page-width",
      view: "FitH",
      search: searchText,
    });
    return `${PDF_VIEWER_BASE_URL}?${params.toString()}`;
  }, [pdfUrl, searchText, source]);

  const triggerViewerSearch = useCallback(
    (direction: "next" | "previous") => {
      if (!searchText || !iframeRef.current?.contentWindow) return;
      const app = (iframeRef.current.contentWindow as Window & {
        PDFViewerApplication?: {
          findController?: {
            executeCommand?: (command: string, options?: Record<string, unknown>) => void;
          };
        };
      }).PDFViewerApplication;

      app?.findController?.executeCommand?.("find", {
        query: searchText,
        caseSensitive: false,
        entireWord: false,
        highlightAll: false,
        findPrevious: direction === "previous",
      });
      app?.findController?.executeCommand?.("findagain", {
        query: searchText,
        caseSensitive: false,
        entireWord: false,
        highlightAll: false,
        findPrevious: direction === "previous",
      });
    },
    [searchText],
  );

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
      setIsReady(false);
      setIframeError(false);
      setIsCopied(false);
    }
  }, [source]);

  const handleCopyCitation = async () => {
    if (!source) return;
    const citationText = [
      title,
      `${filename} • ${pageLabel}`,
      source.text ? `Excerpt: ${source.text}` : undefined,
      source.metadata?.document_id ? `Document ID: ${source.metadata.document_id}` : undefined,
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
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" aria-hidden="true" />
                  <h2 className="truncate text-base font-semibold text-foreground">{title}</h2>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="secondary">{pageLabel}</Badge>
                  <Badge variant="outline">{filename}</Badge>
                  <Badge variant="outline" className="animate-pulse border-primary/50 text-primary">
                    <Sparkles className="mr-1 h-3 w-3" aria-hidden="true" />
                    Highlighted source match
                  </Badge>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => window.open(pdfUrl, "_blank", "noopener,noreferrer")}>
                  <ExternalLink className="mr-2 h-3.5 w-3.5" />
                  Open full PDF
                </Button>
                <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close source inspection">
                  <X className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </div>

            <div className="grid flex-1 gap-0 overflow-hidden lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="flex min-h-0 flex-col bg-muted/20">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-background/70 px-3 py-2 sm:px-4">
                  <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    <Search className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                    PDF inspection workspace
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Button type="button" variant="outline" size="sm" onClick={() => triggerViewerSearch("previous")}>
                      <ChevronLeft className="mr-2 h-3.5 w-3.5" />
                      Previous Match
                    </Button>
                    <Button type="button" variant="outline" size="sm" onClick={() => triggerViewerSearch("next")}>
                      Next Match
                      <ChevronRight className="ml-2 h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>

                <div className="flex-1 p-3 sm:p-4">
                  <div className="flex h-full flex-col overflow-hidden rounded-[28px] border border-border bg-background shadow-inner">
                    {viewerUrl ? (
                      <iframe
                        ref={iframeRef}
                        key={viewerUrl}
                        src={viewerUrl}
                        title="PDF inspection"
                        className="h-full w-full flex-1"
                        onLoad={() => {
                          setIsReady(true);
                          setIframeError(false);
                          window.setTimeout(() => triggerViewerSearch("next"), 900);
                        }}
                        onError={() => {
                          setIsReady(false);
                          setIframeError(true);
                        }}
                      />
                    ) : null}

                    {iframeError && (
                      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted-foreground">
                        The PDF preview could not be loaded. Please confirm the document is available to the backend.
                      </div>
                    )}

                    {!iframeError && !isReady && viewerUrl && (
                      <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
                        Loading source preview…
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <aside className="flex flex-col border-t border-border bg-background/95 p-4 sm:p-5 lg:border-l lg:border-t-0">
                <div className="space-y-4">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Source inspector</p>
                    <h3 className="mt-2 text-lg font-semibold text-foreground">Enterprise evidence</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      Review the original document exactly where this answer was grounded and inspect the surrounding evidence.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-border/70 bg-muted/30 p-4">
                    <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                      <BookOpen className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                      Source details
                    </div>
                    <dl className="mt-3 space-y-2 text-sm">
                      <div className="flex items-start justify-between gap-3">
                        <dt className="text-muted-foreground">Document Name</dt>
                        <dd className="text-right font-medium text-foreground">{filename}</dd>
                      </div>
                      <div className="flex items-start justify-between gap-3">
                        <dt className="text-muted-foreground">Page Number</dt>
                        <dd className="text-right font-medium text-foreground">{pageLabel}</dd>
                      </div>
                      <div className="flex items-start justify-between gap-3">
                        <dt className="text-muted-foreground">Chunk ID</dt>
                        <dd className="text-right font-medium text-foreground">{source.chunk_id}</dd>
                      </div>
                      <div className="flex items-start justify-between gap-3">
                        <dt className="text-muted-foreground">Confidence Score</dt>
                        <dd className="text-right font-medium text-foreground">{confidenceScoreLabel}</dd>
                      </div>
                      <div className="flex items-start justify-between gap-3">
                        <dt className="text-muted-foreground">Retrieval Score</dt>
                        <dd className="text-right font-medium text-foreground">{retrievalScore}%</dd>
                      </div>
                      <div className="flex items-start justify-between gap-3">
                        <dt className="text-muted-foreground">Retrieval Mode</dt>
                        <dd className="text-right font-medium text-foreground">{retrievalMode}</dd>
                      </div>
                    </dl>
                  </div>

                  <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Navigate evidence</p>
                    <div className="mt-3 space-y-3">
                      <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Previous Chunk</p>
                        <p className="mt-2 text-sm text-foreground">
                          {previousSource ? `${getPageLabel(previousSource)} • ${previewText(previousSource)}` : "No earlier retrieval in this answer."}
                        </p>
                      </div>
                      <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Next Chunk</p>
                        <p className="mt-2 text-sm text-foreground">
                          {nextSource ? `${getPageLabel(nextSource)} • ${previewText(nextSource)}` : "No later retrieval in this answer."}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Button type="button" variant="outline" className="w-full justify-start" onClick={handleCopyCitation}>
                      <Copy className="mr-2 h-4 w-4" aria-hidden="true" />
                      {isCopied ? "Citation copied" : "Copy Citation"}
                    </Button>
                    <Button type="button" variant="outline" className="w-full justify-start" onClick={onOpenKnowledgeGraph}>
                      <BookOpen className="mr-2 h-4 w-4" aria-hidden="true" />
                      Open in Knowledge Graph
                    </Button>
                  </div>

                  <div className="rounded-2xl border border-dashed border-border/70 bg-muted/20 p-3 text-sm text-muted-foreground">
                    The viewer opens on the cited page and highlights the related excerpt automatically.
                  </div>
                </div>
              </aside>
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

function previewText(source: RagSource) {
  const rawText = source.text ?? source.metadata?.heading ?? source.metadata?.title ?? "Retrieved excerpt";
  return String(rawText).replace(/\s+/g, " ").slice(0, 84);
}
