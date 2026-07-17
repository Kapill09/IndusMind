import type { RagSource } from "@/types";

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export interface ConfidenceSummary {
  score: number;
  level: ConfidenceLevel;
  label: string;
  breakdown: {
    averageSimilarity: number;
    retrievedChunks: number;
    metadataMatch: boolean;
    structuredBoost: boolean;
    hybridQuality: boolean;
  };
  reasons: string[];
}

export interface StructuredSection {
  id: string;
  title: string;
  content: string;
}

export function calculateConfidenceScore(
  sources?: RagSource[] | null,
  options?: { contextChunks?: number; entitiesCount?: number; latencyMs?: number },
): ConfidenceSummary {
  const normalizedSources = sources ?? [];
  const averageSimilarity = normalizedSources.length
    ? normalizedSources.reduce((sum, source) => sum + (source.score ?? 0.72), 0) / normalizedSources.length
    : 0.72;
  const retrievedChunks = normalizedSources.length || options?.contextChunks || 0;
  const metadataMatch = normalizedSources.some((source) => Boolean(source.metadata?.heading || source.metadata?.title || source.metadata?.document_id));
  const structuredBoost = normalizedSources.some((source) => Boolean(source.metadata?.heading || source.metadata?.title));
  const hybridQuality = normalizedSources.length >= 3 && averageSimilarity >= 0.75;

  let score = Math.round(averageSimilarity * 100 * 0.55 + Math.min(20, retrievedChunks * 3.2));
  if (metadataMatch) score += 10;
  if (structuredBoost) score += 8;
  if (hybridQuality) score += 7;
  if (retrievedChunks === 0) score = Math.max(35, score);
  score = Math.max(0, Math.min(100, score));

  const level: ConfidenceLevel = score >= 80 ? "HIGH" : score >= 60 ? "MEDIUM" : "LOW";

  const reasons = [
    `Average similarity ${(averageSimilarity * 100).toFixed(0)}%`,
    `Retrieved chunks ${retrievedChunks}`,
    metadataMatch ? "Metadata match detected" : "Metadata evidence limited",
    structuredBoost ? "Structured retrieval boost applied" : "No structured boost detected",
    hybridQuality ? "Hybrid retrieval quality is strong" : "Hybrid quality is moderate",
  ];

  return {
    score,
    level,
    label: `${level} CONFIDENCE`,
    breakdown: {
      averageSimilarity,
      retrievedChunks,
      metadataMatch,
      structuredBoost,
      hybridQuality,
    },
    reasons,
  };
}

export function buildStructuredAnswerSections(answer: string, sources?: RagSource[] | null): StructuredSection[] {
  const normalizedAnswer = answer.replace(/\r/g, "").trim();
  if (!normalizedAnswer) {
    return [
      { id: "summary", title: "Summary", content: "No answer content was returned for this request." },
    ];
  }

  const sectionPattern = /^(#{1,3})\s+(.+)$/gm;
  const sections: StructuredSection[] = [];
  let match;
  
  const firstHeaderMatch = sectionPattern.exec(normalizedAnswer);
  if (firstHeaderMatch && firstHeaderMatch.index > 0) {
     const preamble = normalizedAnswer.slice(0, firstHeaderMatch.index).trim();
     if (preamble) {
         sections.push({ id: "overview", title: "Overview", content: preamble });
     }
  }
  
  sectionPattern.lastIndex = 0;

  let currentTitle = "Overview";
  let currentContentStart = 0;

  while ((match = sectionPattern.exec(normalizedAnswer)) !== null) {
    if (currentContentStart > 0 || currentTitle !== "Overview") {
       const content = normalizedAnswer.slice(currentContentStart, match.index).trim();
       if (content) {
           sections.push({
               id: currentTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
               title: currentTitle,
               content: content
           });
       }
    }
    
    currentTitle = match[2].trim();
    currentContentStart = match.index + match[0].length;
  }
  
  if (currentContentStart > 0 && currentContentStart < normalizedAnswer.length) {
     const content = normalizedAnswer.slice(currentContentStart).trim();
     if (content) {
         sections.push({
             id: currentTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
             title: currentTitle,
             content: content
         });
     }
  }

  if (sections.length === 0) {
      sections.push({ id: "overview", title: "Analysis", content: normalizedAnswer });
  }

  return sections;
}

export function getSourcePreviewText(source: RagSource, maxLength = 110) {
  const text = (source.text ?? source.metadata?.heading ?? source.metadata?.title ?? "Grounded snippet from the uploaded document.").toString();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1).trimEnd()}…` : text;
}

export function getSourceTitle(source: RagSource, maxLength = 52) {
  const rawTitle = source.metadata?.heading || source.metadata?.title || source.metadata?.filename || "Uploaded document";
  const normalizedTitle = String(rawTitle).replace(/\s+/g, " ").trim();
  return normalizedTitle.length > maxLength
    ? `${normalizedTitle.slice(0, maxLength - 1).trimEnd()}…`
    : normalizedTitle;
}

export function getSourceFilename(source: RagSource) {
  return String(source.metadata?.filename ?? "Uploaded document");
}

export function getPageLabel(source: RagSource) {
  if (source.page_start && source.page_end) {
    return source.page_start === source.page_end ? `Page ${source.page_start}` : `Pages ${source.page_start}-${source.page_end}`;
  }
  if (source.page_start) return `Page ${source.page_start}`;
  if (source.page_end) return `Page ${source.page_end}`;
  return "Page unknown";
}

export function buildCitationText(source: RagSource) {
  const filename = source.metadata?.filename ?? "Uploaded document";
  const pageLabel = getPageLabel(source);
  const title = source.metadata?.heading || source.metadata?.title || filename;
  return `${title} (${filename}, ${pageLabel})`;
}3