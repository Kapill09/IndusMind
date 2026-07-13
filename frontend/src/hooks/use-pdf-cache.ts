import { useEffect, useRef } from "react";

interface PDFCacheEntry {
  url: string;
  blob: Blob;
  timestamp: number;
}

const PDF_CACHE_KEY = "indus-mind-pdf-cache";
const MAX_CACHE_SIZE = 5; // Maximum number of PDFs to cache
const CACHE_EXPIRY = 1000 * 60 * 60; // 1 hour

/**
 * Hook to cache PDF files in memory for faster subsequent loads
 * Implements LRU (Least Recently Used) eviction strategy
 */
export function usePDFCache() {
  const cacheRef = useRef<Map<string, PDFCacheEntry>>(new Map());

  useEffect(() => {
    // Initialize cache from localStorage on mount
    try {
      const stored = localStorage.getItem(PDF_CACHE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Only restore URLs, not blobs (blobs can't be serialized)
        cacheRef.current = new Map(Object.entries(parsed));
      }
    } catch {
      // Ignore errors
    }
  }, []);

  const getCachedPDF = (url: string): Blob | null => {
    const entry = cacheRef.current.get(url);
    if (!entry) return null;

    // Check if cache entry is expired
    if (Date.now() - entry.timestamp > CACHE_EXPIRY) {
      cacheRef.current.delete(url);
      return null;
    }

    // Update timestamp for LRU
    entry.timestamp = Date.now();
    return entry.blob;
  };

  const cachePDF = async (url: string): Promise<Blob | null> => {
    try {
      // Check if already cached
      const cached = getCachedPDF(url);
      if (cached) return cached;

      // Fetch PDF
      const response = await fetch(url);
      if (!response.ok) return null;

      const blob = await response.blob();

      // Implement LRU eviction if cache is full
      if (cacheRef.current.size >= MAX_CACHE_SIZE) {
        // Find oldest entry
        let oldestKey = "";
        let oldestTime = Date.now();

        for (const [key, entry] of cacheRef.current.entries()) {
          if (entry.timestamp < oldestTime) {
            oldestTime = entry.timestamp;
            oldestKey = key;
          }
        }

        if (oldestKey) {
          cacheRef.current.delete(oldestKey);
        }
      }

      // Add to cache
      cacheRef.current.set(url, {
        url,
        blob,
        timestamp: Date.now(),
      });

      // Persist cache metadata to localStorage (not blobs)
      try {
        const cacheMetadata: Record<string, { url: string; timestamp: number }> = {};
        for (const [key, entry] of cacheRef.current.entries()) {
          cacheMetadata[key] = { url: entry.url, timestamp: entry.timestamp };
        }
        localStorage.setItem(PDF_CACHE_KEY, JSON.stringify(cacheMetadata));
      } catch {
        // Ignore localStorage errors
      }

      return blob;
    } catch {
      return null;
    }
  };

  const clearCache = () => {
    cacheRef.current.clear();
    try {
      localStorage.removeItem(PDF_CACHE_KEY);
    } catch {
      // Ignore errors
    }
  };

  const getCacheSize = () => cacheRef.current.size;

  return {
    getCachedPDF,
    cachePDF,
    clearCache,
    getCacheSize,
  };
}
