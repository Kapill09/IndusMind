import { useEffect } from "react";
import { X, FileText, FileSearch, HelpCircle } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import type { RagSource } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface SourceDrawerProps {
  source: RagSource | null;
  onClose: () => void;
}

export function SourceDrawer({ source, onClose }: SourceDrawerProps) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && source) {
        onClose();
      }
    };
    
    if (source) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [source, onClose]);

  const metadataEntries = source
    ? Object.entries(source.metadata).filter(
        ([key, val]) => val !== null && val !== undefined && key !== "filename" && key !== "page_start" && key !== "page_end",
      )
    : [];

  return (
    <AnimatePresence>
      {source && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm"
            onClick={onClose}
          />
          
          {/* Drawer */}
          <motion.div
            initial={{ x: "100%", boxShadow: "none" }}
            animate={{ 
              x: 0, 
              boxShadow: "-10px 0px 30px -15px rgba(0,0,0,0.2)"
            }}
            exit={{ x: "100%", boxShadow: "none" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-md border-l border-border bg-card p-6 shadow-xl flex flex-col sm:max-w-lg"
            role="dialog"
            aria-modal="true"
            aria-labelledby="source-drawer-title"
          >
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <h2 id="source-drawer-title" className="text-lg font-semibold flex items-center gap-2">
                <FileSearch className="h-5 w-5 text-primary" aria-hidden="true" />
                Source Details
              </h2>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onClose}
                aria-label="Close drawer"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            
            <div className="flex-1 overflow-y-auto py-6 space-y-6">
              <div className="flex gap-4">
                <div className="mt-1 flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText className="h-6 w-6" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-medium text-base text-foreground break-words">
                    {source.metadata.filename || "Uploaded document"}
                  </h3>
                  <div className="mt-1.5 flex flex-wrap gap-2">
                    <Badge variant="secondary">
                      {getPageLabel(source)}
                    </Badge>
                    <Badge variant="outline">
                      Relevance {Math.round((source.score ?? 0) * 100)}%
                    </Badge>
                  </div>
                </div>
              </div>
              
              <div className="space-y-3">
                <h4 className="text-sm font-semibold flex items-center gap-1.5 text-foreground">
                  <HelpCircle className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  Retrieved Context
                </h4>
                <div className="rounded-xl border border-border bg-muted/30 p-4 text-sm leading-7 text-foreground shadow-sm">
                  {source.text ? (
                    <div className="whitespace-pre-wrap">{source.text}</div>
                  ) : (
                    <p className="text-muted-foreground italic">No chunk text available.</p>
                  )}
                </div>
              </div>
              
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-foreground">Metadata</h4>
                {metadataEntries.length > 0 ? (
                  <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm text-left">
                      <tbody className="divide-y divide-border">
                        {metadataEntries.map(([key, value]) => (
                          <tr key={key} className="bg-card">
                            <td className="px-4 py-2 font-medium text-muted-foreground w-1/3 bg-muted/10 border-r border-border capitalize">
                              {key.replace(/_/g, " ")}
                            </td>
                            <td className="px-4 py-2 text-foreground font-mono text-xs break-all">
                              {String(value)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-border bg-muted/20 p-4 text-sm text-muted-foreground">
                    No additional metadata is available for this source.
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function getPageLabel(source: RagSource) {
  if (source.page_start && source.page_end) {
    return source.page_start === source.page_end
      ? `Page ${source.page_start}`
      : `Pages ${source.page_start}-${source.page_end}`;
  }

  if (source.page_start) return `Page ${source.page_start}`;
  if (source.page_end) return `Page ${source.page_end}`;
  return "Page unknown";
}
