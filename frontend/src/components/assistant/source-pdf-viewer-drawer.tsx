import { useEffect, useMemo, useState } from "react";
import { X, FileText, ExternalLink, Sparkles } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import type { RagSource } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface SourcePdfViewerDrawerProps {
  source: RagSource | null;
  onClose: () => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export function SourcePdfViewerDrawer({ source, onClose }: SourcePdfViewerDrawerProps) {
  const [iframeError, setIframeError] = useState(false);
  const [isReady, setIsReady] = useState(false);

  const pdfUrl = useMemo(() => {
    if (!source) return "";
    const documentId = source.metadata?.document_id?.toString().trim();
    const filename = source.metadata?.filename?.toString().trim();
    const params = new URLSearchParams();
    if (documentId) params.set("document_id", documentId);
    if (filename) params.set("filename", filename);
    const basePath = `${API_BASE_URL}/documents/preview`;
    return params.toString() ? `${basePath}?${params.toString()}` : basePath;
  }, [source]);

  const viewerUrl = useMemo(() => {
    if (!pdfUrl) return "";
    const pageNumber = source?.page_start ?? source?.metadata?.page_start ?? 1;
    const searchText = String(source?.text ?? source?.metadata?.heading ?? source?.metadata?.title ?? "").trim();
    const normalizedSearch = searchText.replace(/\s+/g, " ").slice(0, 140);
    const params = new URLSearchParams({ file: pdfUrl });
    if (pageNumber) params.set("page", String(pageNumber));
    if (normalizedSearch) params.set("search", normalizedSearch);
    return `https://mozilla.github.io/pdf.js/web/viewer.html?${params.toString()}`;
  }, [pdfUrl, source]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && source) {
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
    }
  }, [source]);

  const pageLabel = source ? getPageLabel(source) : "Page unknown";
  const title = source?.metadata?.heading || source?.metadata?.title || source?.metadata?.filename || "Source document";

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
            className="fixed inset-y-0 right-0 z-[70] flex w-full max-w-6xl flex-col border-l border-border bg-card shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-label="PDF citation preview"
          >
            <div className="flex items-center justify-between border-b border-border px-4 py-3 sm:px-6">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" aria-hidden="true" />
                  <h2 className="truncate text-base font-semibold text-foreground">{title}</h2>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="secondary">{pageLabel}</Badge>
                  <Badge variant="outline">{source.metadata?.filename ?? "Uploaded document"}</Badge>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(pdfUrl, "_blank", "noopener,noreferrer")}
                  className="hidden sm:inline-flex"
                >
                  <ExternalLink className="mr-2 h-3.5 w-3.5" />
                  Open full PDF
                </Button>
                <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close PDF preview">
                  <X className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </div>

            <div className="flex-1 bg-muted/20 p-3 sm:p-4">
              <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-inner">
                {viewerUrl ? (
                  <>
                    <div className="flex items-center gap-2 border-b border-border bg-muted/20 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                      <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                      Jumping to the cited page and searching for the related excerpt.
                    </div>
                    <iframe
                      key={viewerUrl}
                      src={viewerUrl}
                      title="PDF preview"
                      className="h-full w-full flex-1"
                      onLoad={() => {
                        setIsReady(true);
                        setIframeError(false);
                      }}
                      onError={() => {
                        setIsReady(false);
                        setIframeError(true);
                      }}
                    />
                  </>
                ) : null}

                {iframeError && (
                  <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted-foreground">
                    The PDF preview could not be loaded. Please confirm the document is available in the upload folder.
                  </div>
                )}

                {!iframeError && !isReady && viewerUrl && (
                  <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
                    Loading document preview…
                  </div>
                )}
              </div>
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
