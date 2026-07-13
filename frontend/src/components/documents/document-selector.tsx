import React from "react";
import { Button } from "@/components/ui/button";
import { useSelectedDocuments } from "@/hooks/use-selected-documents";

export function DocumentSelector({ compact }: { compact?: boolean }) {
  const { documents, selected, toggle, selectedCount } = useSelectedDocuments();
  const [open, setOpen] = React.useState(false);

  return (
    <div className="relative inline-block">
      <Button size={compact ? "sm" : "md"} variant="outline" onClick={() => setOpen((s) => !s)}>
        Sources ({selectedCount})
      </Button>
      {open && (
        <div className="absolute right-0 bottom-full mb-2 z-50 w-80 rounded-lg border border-border bg-card p-3 shadow-md">
          <div className="text-xs text-muted-foreground mb-2">Toggle sources used by AI and graph</div>
          <div className="max-h-64 overflow-y-auto space-y-1">
            {documents.length === 0 ? (
              <div className="text-sm text-muted-foreground">No uploaded documents</div>
            ) : (
              documents.map((doc) => {
                const docId = doc.document_id;
                const isChecked = selected.includes(docId);
                return (
                  <label 
                    key={docId} 
                    className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-accent/50 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggle(docId)}
                      className="cursor-pointer"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-sm font-medium">{doc.filename}</div>
                      <div className="text-xs text-muted-foreground">
                        {doc.chunks.toLocaleString()} chunks
                      </div>
                    </div>
                  </label>
                );
              })
            )}
          </div>
          {documents.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
              Selected: {selectedCount} {selectedCount === 1 ? 'Document' : 'Documents'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
