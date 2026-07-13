import { memo, useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Download,
  Search,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PDFHighlightLayer } from "./pdf-highlight-layer";

// Import CSS for react-pdf
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Configure PDF.js worker - use CDN for simplicity
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

interface PDFViewerProps {
  pdfUrl: string;
  initialPage?: number;
  highlightText?: string;
  onClose?: () => void;
}

export const PDFViewer = memo(function PDFViewer({
  pdfUrl,
  initialPage = 1,
  highlightText,
  onClose,
}: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [scale, setScale] = useState<number>(1.0);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [highlightState, setHighlightState] = useState<"idle" | "found" | "missing">("idle");
  const pageContainerRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const normalizeText = useCallback((text: string): string => {
    return text
      .toLowerCase()
      .replace(/\s+/g, " ")
      .replace(/[^\w\s]/g, "")
      .trim();
  }, []);

  const scrollToHighlightedText = useCallback(() => {
    if (!highlightText || !pageContainerRef.current) {
      setHighlightState("missing");
      return false;
    }

    const textLayerDiv = pageContainerRef.current.querySelector(".react-pdf__Page__textContent");
    if (!textLayerDiv) {
      setHighlightState("missing");
      return false;
    }

    const spans = textLayerDiv.querySelectorAll("span");
    const normalizedHighlight = normalizeText(highlightText);

    let accumulatedText = "";
    let matchingSpans: HTMLElement[] = [];

    for (let i = 0; i < spans.length; i++) {
      const span = spans[i] as HTMLElement;
      const spanText = span.textContent || "";
      accumulatedText += " " + spanText;
      matchingSpans.push(span);

      const normalizedAccumulated = normalizeText(accumulatedText);

      if (normalizedAccumulated.includes(normalizedHighlight)) {
        if (matchingSpans.length > 0) {
          matchingSpans[0].scrollIntoView({
            behavior: "smooth",
            block: "center",
          });
          setHighlightState("found");
          return true;
        }
        break;
      }

      if (accumulatedText.length > normalizedHighlight.length * 2) {
        accumulatedText = spanText;
        matchingSpans = [span];
      }
    }

    setHighlightState("missing");
    return false;
  }, [highlightText, normalizeText]);

  // Update current page when initialPage changes
  useEffect(() => {
    setCurrentPage(initialPage);
  }, [initialPage]);

  // Auto-scroll to highlighted text after page renders
  useEffect(() => {
    setHighlightState("idle");
    if (highlightText && pageContainerRef.current && !isLoading) {
      const timer = setTimeout(() => {
        scrollToHighlightedText();
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [currentPage, highlightText, scale, isLoading, scrollToHighlightedText]);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setCurrentPage((prev) => Math.min(numPages, Math.max(1, prev)));
    setIsLoading(false);
  }, []);

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error("PDF load error:", error);
    setIsLoading(false);
  }, []);

  const goToPreviousPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setCurrentPage((prev) => Math.min(numPages, prev + 1));
  }, [numPages]);

  const zoomIn = useCallback(() => {
    setScale((prev) => Math.min(3.0, prev + 0.2));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((prev) => Math.max(0.5, prev - 0.2));
  }, []);

  const handleFullscreen = useCallback(() => {
    if (containerRef.current) {
      if (!document.fullscreenElement) {
        containerRef.current.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    }
  }, []);

  const handleDownload = useCallback(() => {
    const link = document.createElement("a");
    link.href = pdfUrl;
    link.download = "document.pdf";
    link.click();
  }, [pdfUrl]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
        return;
      }

      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault();
        goToNextPage();
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        goToPreviousPage();
      } else if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        zoomIn();
      } else if (event.key === "-") {
        event.preventDefault();
        zoomOut();
      } else if (event.key === "Escape") {
        onClose?.();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goToNextPage, goToPreviousPage, zoomIn, zoomOut, onClose]);

  const handleSearch = useCallback(() => {
    if (!searchTerm.trim()) return;
    const textLayerDiv = pageContainerRef.current?.querySelector(".react-pdf__Page__textContent");
    if (!textLayerDiv) return;

    const allText = textLayerDiv.textContent || "";
    if (normalizeText(allText).includes(normalizeText(searchTerm))) {
      alert(`Found "${searchTerm}" on page ${currentPage}`);
    } else {
      alert(`"${searchTerm}" not found on this page`);
    }
  }, [searchTerm, currentPage, normalizeText]);

  return (
    <div ref={containerRef} className="flex h-full flex-col bg-background">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-border bg-card px-4 py-2">
        <div className="flex items-center gap-2">
          {/* Page Navigation */}
          <Button
            variant="ghost"
            size="sm"
            onClick={goToPreviousPage}
            disabled={currentPage <= 1}
            className="h-8 w-8 p-0"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium">
            Page {currentPage} of {numPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={goToNextPage}
            disabled={currentPage >= numPages}
            className="h-8 w-8 p-0"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>

          <div className="mx-2 h-6 w-px bg-border" />

          {/* Zoom Controls */}
          <Button
            variant="ghost"
            size="sm"
            onClick={zoomOut}
            disabled={scale <= 0.5}
            className="h-8 w-8 p-0"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium">{Math.round(scale * 100)}%</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={zoomIn}
            disabled={scale >= 3.0}
            className="h-8 w-8 p-0"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          {isSearchOpen ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search in document..."
                className="h-8 rounded border border-border bg-background px-2 text-sm"
                autoFocus
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSearch}
                className="h-8 w-8 p-0"
              >
                <Search className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setIsSearchOpen(false);
                  setSearchTerm("");
                }}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsSearchOpen(true)}
              className="h-8 gap-1.5 px-2 text-xs"
            >
              <Search className="h-4 w-4" />
              Search
            </Button>
          )}

          {/* Fullscreen */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleFullscreen}
            className="h-8 gap-1.5 px-2 text-xs"
          >
            <Maximize2 className="h-4 w-4" />
            Fullscreen
          </Button>

          {/* Download */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDownload}
            className="h-8 gap-1.5 px-2 text-xs"
          >
            <Download className="h-4 w-4" />
            Download
          </Button>

          {onClose && (
            <>
              <div className="mx-2 h-6 w-px bg-border" />
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-8 gap-1.5 px-2 text-xs"
              >
                <X className="h-4 w-4" />
                Close
              </Button>
            </>
          )}
        </div>
      </div>

      {/* PDF Content */}
      <div className="flex-1 overflow-auto bg-muted/20 p-4">
        <div className="mx-auto flex justify-center">
          <div ref={pageContainerRef} className="relative">
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className="flex h-96 items-center justify-center">
                  <div className="text-center">
                    <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                    <p className="mt-2 text-sm text-muted-foreground">Loading PDF...</p>
                  </div>
                </div>
              }
              error={
                <div className="flex h-96 items-center justify-center">
                  <div className="text-center">
                    <p className="text-sm font-medium text-destructive">Failed to load PDF</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Please check the file and try again
                    </p>
                  </div>
                </div>
              }
            >
              <Page
                pageNumber={currentPage}
                scale={scale}
                renderTextLayer={true}
                renderAnnotationLayer={true}
                className="shadow-lg"
                loading={
                  <div className="flex h-96 w-96 items-center justify-center bg-muted/20">
                    <div className="text-center">
                      <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                      <p className="mt-2 text-xs text-muted-foreground">Rendering page...</p>
                    </div>
                  </div>
                }
                error={
                  <div className="flex h-96 w-96 items-center justify-center bg-muted/20">
                    <p className="text-xs text-muted-foreground">Failed to render page</p>
                  </div>
                }
              />
            </Document>
            
            {highlightText && !isLoading && (
              <>
                {highlightState === "missing" && (
                  <div className="mb-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    Highlighted passage unavailable
                  </div>
                )}
                <PDFHighlightLayer
                  highlightText={highlightText}
                  pageNumber={currentPage}
                  scale={scale}
                  containerRef={pageContainerRef}
                  onHighlightStateChange={setHighlightState}
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});
