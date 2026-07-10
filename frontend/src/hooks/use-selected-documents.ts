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

  // Helper: derive the vectordb document id from a filename (stem without ext)
  const filenameToDocId = (filename: string | undefined) => {
    if (!filename) return "";
    const parts = filename.split("/").pop()?.split(".") ?? [filename];
    parts.pop();
    return (parts.join(".") || filename).replace(/\s+/g, "-").toLowerCase();
  };

  // If there are no saved selections, default to all known documents (use filename stem)
  useEffect(() => {
    if (selected.length === 0 && documents.length > 0) {
      setSelected(documents.map((d) => filenameToDocId(d.filename)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documents.length]);

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
