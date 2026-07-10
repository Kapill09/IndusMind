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
  // The document ID stored in the database is the stem of the filename (filename without the extension)
  // e.g., "my-document (1).pdf" -> "my-document (1)"
  const filenameToDocId = (filename: string | undefined) => {
    if (!filename) return "";
    const basename = filename.split("/").pop() || filename;
    // Remove the last extension only (e.g., .pdf)
    const lastDotIndex = basename.lastIndexOf(".");
    if (lastDotIndex === -1) return basename;
    return basename.substring(0, lastDotIndex);
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
