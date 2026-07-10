import React from "react";
import { Button } from "@/components/ui/button";
import { useSelectedDocuments } from "@/hooks/use-selected-documents";

export function DocumentSelector({ compact }: { compact?: boolean }) {
  const { documents, selected, toggle, selectedCount } = useSelectedDocuments();
  const [open, setOpen] = React.useState(false);

  const filenameToDocId = (filename?: string) => {
    if (!filename) return "";
    const parts = filename.split("/").pop()?.split(".") ?? [filename];
    parts.pop();
    return parts.join(".") || filename;
  };

  return (
    <div className="relative inline-block">
      <Button size={compact ? "sm" : "md"} variant="outline" onClick={() => setOpen((s) => !s)}>
        Sources ({selectedCount})
      </Button>
      {open && (
        <div className="absolute right-0 bottom-full mb-2 z-50 w-64 rounded-lg border border-border bg-card p-3 shadow-md">
          <div className="text-xs text-muted-foreground">Toggle sources used by AI and graph</div>
          <div className="mt-2 max-h-48 overflow-y-auto">
            {documents.length === 0 ? (
              <div className="text-sm text-muted-foreground">No uploaded documents</div>
            ) : (
              documents.map((doc) => {
                const docId = filenameToDocId(doc.filename);
                return (
                  <label key={docId || doc.id} className="flex items-center gap-2 py-1">
                    <input
                      type="checkbox"
                      checked={selected.includes(docId)}
                      onChange={() => toggle(docId)}
                    />
                    <span className="truncate text-sm">{doc.filename}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
