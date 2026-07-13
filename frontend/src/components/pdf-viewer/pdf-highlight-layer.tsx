import { useEffect, useRef, useState } from "react";

interface HighlightRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface PDFHighlightLayerProps {
  highlightText: string;
  pageNumber: number;
  scale: number;
  containerRef: React.RefObject<HTMLElement>;
  onHighlightStateChange?: (state: "found" | "missing") => void;
}

/**
 * Overlay component that highlights specific text on a PDF page
 * Uses fuzzy matching to find text across multiple spans in the PDF text layer
 */
export function PDFHighlightLayer({
  highlightText,
  pageNumber,
  scale,
  containerRef,
  onHighlightStateChange,
}: PDFHighlightLayerProps) {
  const [highlights, setHighlights] = useState<HighlightRect[]>([]);
  const highlightLayerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Wait for PDF text layer to render
    const timer = setTimeout(() => {
      findAndHighlightText();
    }, 300);

    return () => clearTimeout(timer);
  }, [highlightText, pageNumber, scale]);

  const normalizeText = (text: string): string => {
    return text
      .toLowerCase()
      .replace(/\s+/g, " ")
      .replace(/[^\w\s]/g, "")
      .trim();
  };

  const findAndHighlightText = () => {
    if (!highlightText || !containerRef.current) {
      setHighlights([]);
      onHighlightStateChange?.("missing");
      return;
    }

    const textLayer = containerRef.current.querySelector(".react-pdf__Page__textContent");
    if (!textLayer) {
      setHighlights([]);
      onHighlightStateChange?.("missing");
      return;
    }

    const spans = Array.from(textLayer.querySelectorAll("span")) as HTMLElement[];
    const normalizedHighlight = normalizeText(highlightText);
    const words = normalizedHighlight.split(" ");
    
    // Use a sliding window approach to match text across spans
    const matchingSpans: HTMLElement[] = [];
    let accumulatedText = "";
    let startIndex = 0;

    for (let i = 0; i < spans.length; i++) {
      const span = spans[i];
      const spanText = span.textContent || "";
      
      accumulatedText += " " + spanText;
      const normalized = normalizeText(accumulatedText);

      // Check if we have a match
      if (normalized.includes(normalizedHighlight) || 
          fuzzyMatch(normalized, normalizedHighlight)) {
        // Found match - collect all spans from startIndex to current
        for (let j = startIndex; j <= i; j++) {
          matchingSpans.push(spans[j]);
        }
        break;
      }

      // If accumulated text is too long, slide the window
      if (accumulatedText.length > normalizedHighlight.length * 2) {
        startIndex++;
        accumulatedText = spans.slice(startIndex, i + 1)
          .map(s => s.textContent)
          .join(" ");
      }
    }

    // Create highlight rectangles from matching spans
    if (matchingSpans.length > 0) {
      onHighlightStateChange?.("found");
      const rects = matchingSpans.map(span => {
        const rect = span.getBoundingClientRect();
        const pageRect = textLayer.getBoundingClientRect();
        
        return {
          left: rect.left - pageRect.left,
          top: rect.top - pageRect.top,
          width: rect.width,
          height: rect.height,
        };
      });

      setHighlights(rects);

      // Scroll first highlight into view
      if (matchingSpans[0]) {
        matchingSpans[0].scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    } else {
      setHighlights([]);
      onHighlightStateChange?.("missing");
    }
  };

  const fuzzyMatch = (text: string, pattern: string): boolean => {
    // Allow up to 10% character difference for fuzzy matching
    const maxDiff = Math.ceil(pattern.length * 0.1);
    
    for (let i = 0; i <= text.length - pattern.length; i++) {
      const substring = text.substring(i, i + pattern.length);
      const diff = levenshteinDistance(substring, pattern);
      
      if (diff <= maxDiff) {
        return true;
      }
    }
    
    return false;
  };

  const levenshteinDistance = (str1: string, str2: string): number => {
    const matrix: number[][] = [];

    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }

    return matrix[str2.length][str1.length];
  };

  if (highlights.length === 0) {
    return null;
  }

  return (
    <div
      ref={highlightLayerRef}
      className="pointer-events-none absolute inset-0"
      style={{ zIndex: 2 }}
    >
      {highlights.map((rect, index) => (
        <div
          key={index}
          className="absolute animate-pulse"
          style={{
            left: `${rect.left}px`,
            top: `${rect.top}px`,
            width: `${rect.width}px`,
            height: `${rect.height}px`,
            backgroundColor: "rgba(255, 235, 59, 0.4)", // Yellow highlight
            border: "1px solid rgba(255, 193, 7, 0.6)",
            borderRadius: "2px",
            animation: "fadeIn 0.5s ease-in",
          }}
        />
      ))}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
