import { useEffect, useState, useCallback } from "react";
import { useLocalDocuments } from "@/hooks/use-local-documents";

const STORAGE_KEY = "indus-mind-selected-documents";
const EVENT_KEY = "indus-mind-selected-documents-changed";

function readFromStorage(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as string[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function useSelectedDocuments() {
  const { documents } = useLocalDocuments();
  const [selected, setLocalSelected] = useState<string[]>(readFromStorage);

  useEffect(() => {
    const handleStorageChange = () => {
      setLocalSelected(readFromStorage());
    };

    window.addEventListener(EVENT_KEY, handleStorageChange);
    window.addEventListener("storage", (e) => {
      if (e.key === STORAGE_KEY) handleStorageChange();
    });

    return () => {
      window.removeEventListener(EVENT_KEY, handleStorageChange);
      window.removeEventListener("storage", handleStorageChange);
    };
  }, []);

  const setSelected = useCallback((updater: string[] | ((curr: string[]) => string[])) => {
    setLocalSelected((current) => {
      const next = typeof updater === "function" ? updater(current) : updater;
      
      // Only trigger updates if the array actually changed
      if (JSON.stringify(current) === JSON.stringify(next)) return current;
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      console.log("Selection changed");
      console.log("Current selected IDs:", next);
      window.dispatchEvent(new Event(EVENT_KEY));
      return next;
    });
  }, []);

  // Prune stale selections: remove any selected document_id that no longer
  // exists in the live backend inventory.  This prevents sending IDs to the
  // retrieval API that ChromaDB can no longer resolve.
  useEffect(() => {
    if (documents.length === 0) return;
    const validIds = new Set(documents.map((d) => d.document_id));
    setSelected((current) => {
      const pruned = current.filter((id) => validIds.has(id));
      return pruned.length === current.length ? current : pruned;
    });
  }, [documents, setSelected]);

  const toggle = useCallback((id: string) => {
    setSelected((current) => (current.includes(id) ? current.filter((i) => i !== id) : [...current, id]));
  }, [setSelected]);

  const setAll = useCallback((ids: string[]) => setSelected(ids), [setSelected]);
  const clear = useCallback(() => setSelected([]), [setSelected]);
  const isSelected = useCallback((id: string) => selected.includes(id), [selected]);

  const selectedCount = selected.length;

  return {
    selected,
    toggle,
    setAll,
    clear,
    isSelected,
    selectedCount,
    documents,
  };
}
