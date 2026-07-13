import { useEffect, useState } from "react";
import { useLocalDocuments } from "@/hooks/use-local-documents";

const STORAGE_KEY = "indus-mind-selected-documents";

export function useSelectedDocuments() {
  const { documents } = useLocalDocuments();
  const [selected, setSelected] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw) as string[];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(selected));
  }, [selected]);

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
  }, [documents]);

  const toggle = (id: string) => {
    setSelected((current) => (current.includes(id) ? current.filter((i) => i !== id) : [...current, id]));
  };

  const setAll = (ids: string[]) => setSelected(ids);
  const clear = () => setSelected([]);
  const isSelected = (id: string) => selected.includes(id);

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
