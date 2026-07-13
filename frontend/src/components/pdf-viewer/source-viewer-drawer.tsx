import { memo, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight, Copy, FileText, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PDFViewer } from "./pdf-viewer";
import type { RagSource } from "@/types";

interface SourceViewerDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  source: RagSource | null;
  allSources?: RagSource[];
  confidence?: number;
  onNavigate?: (source: RagSource) => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export const SourceViewerDrawer = memo(function SourceViewerDrawer({
  isOpen,
  onClose,
  source,
  allSources = [],
  confidence,
  onNavigate,
}: SourceViewerDrawerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Update current index when source changes
  useEffect(() => {
    if (source && allSources.length > 0) {
      const index = allSources.findIndex((s) => s.chunk_id === source.chunk_id);
      if (index >= 0) {
        setCurrentIndex(index);
      }
    }
  }, [source, allSources]);

  if (!source) return null;

  const documentId = source.metadata?.document_id || "";
  const filename = source.metadata?.filename || "document.pdf";
  const pageStart = source.page_start || 1;
  const pageEnd = source.page_end;
  const chunkScore = source.score ? Math.round(source.score * 100) : null;

  // Construct PDF URL
  const pdfUrl = documentId
    ? `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/pdf`
    : "";

  const handlePrevious = () => {
    if (currentIndex > 0 && onNavigate) {
      const prevSource = allSources[currentIndex - 1];
      setCurrentIndex(currentIndex - 1);
      onNavigate(prevSource);
    }
  };

  const handleNext = () => {
    if (currentIndex < allSources.length - 1 && onNavigate) {
      const nextSource = allSources[currentIndex + 1];
      setCurrentIndex(currentIndex + 1);
      onNavigate(nextSource);
    }
  };

  const handleCopyCitation = () => {
    const citation = `${filename}, Page ${pageStart}${pageEnd && pageEnd !== pageStart ? `-${pageEnd}` : ""}`;
    navigator.clipboard.writeText(citation);
  };

  const hasMultipleSources = allSources.length > 1;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 z-50 h-full w-full bg-background shadow-2xl lg:w-4/5 xl:w-3/4"
          >
            <div className="flex h-full flex-col">
              {/* Header with Citation Metadata */}
              <div className="border-b border-border bg-card px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <FileText className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h2 className="truncate text-lg font-semibold text-foreground">
                          {filename}
                        </h2>
                        <p className="text-sm text-muted-foreground">
                          Source Evidence from AI Assistant
                        </p>
                      </div>
                    </div>

                    {/* Metadata Chips */}
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Page Info */}
                      <div className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs">
                        <span className="font-medium text-muted-foreground">Page:</span>
                        <span className="font-semibold text-foreground">
                          {pageStart}
                          {pageEnd && pageEnd !== pageStart && `–${pageEnd}`}
                        </span>
                      </div>

                      {/* Chunk Score */}
                      {chunkScore !== null && (
                        <div className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs">
                          <TrendingUp className="h-3 w-3 text-primary" />
                          <span className="font-medium text-muted-foreground">Relevance:</span>
                          <span className="font-semibold text-foreground">{chunkScore}%</span>
                        </div>
                      )}

                      {/* Confidence */}
                      {confidence !== undefined && (
                        <div className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs">
                          <span className="font-medium text-muted-foreground">Confidence:</span>
                          <span className="font-semibold text-foreground">{Math.round(confidence)}%</span>
                        </div>
                      )}

                      {/* Chunk ID */}
                      <div className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs">
                        <span className="font-medium text-muted-foreground">Chunk:</span>
                        <span className="font-mono text-xs text-foreground">
                          {source.chunk_id.split("_").slice(-2).join("_")}
                        </span>
                      </div>
                    </div>

                    {/* Source Preview Text */}
                    {source.text && (
                      <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                          Highlighted Text
                        </p>
                        <p className="line-clamp-3 text-sm leading-relaxed text-foreground">
                          {source.text.length > 200 ? source.text.substring(0, 200) + "..." : source.text}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Close Button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="ml-4 h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-5 w-5" />
                  </Button>
                </div>

                {/* Action Buttons */}
                <div className="mt-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCopyCitation}
                      className="h-8 gap-1.5 px-3 text-xs"
                    >
                      <Copy className="h-3.5 w-3.5" />
                      Copy Citation
                    </Button>

                    {hasMultipleSources && (
                      <>
                        <div className="mx-1 h-6 w-px bg-border" />
                        <div className="flex items-center gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handlePrevious}
                            disabled={currentIndex === 0}
                            className="h-8 w-8 p-0"
                          >
                            <ChevronLeft className="h-4 w-4" />
                          </Button>
                          <span className="px-2 text-xs font-medium text-muted-foreground">
                            {currentIndex + 1} of {allSources.length}
                          </span>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleNext}
                            disabled={currentIndex === allSources.length - 1}
                            className="h-8 w-8 p-0"
                          >
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1">
                    <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                    <span className="text-xs font-medium text-primary">Source used by AI</span>
                  </div>
                </div>
              </div>

              {/* PDF Viewer */}
              <div className="flex-1 overflow-hidden">
                {pdfUrl ? (
                  <PDFViewer
                    pdfUrl={pdfUrl}
                    initialPage={pageStart}
                    highlightText={source.text}
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <div className="text-center">
                      <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
                      <p className="mt-4 text-sm font-medium text-foreground">PDF not available</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        The source document could not be loaded
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
});
