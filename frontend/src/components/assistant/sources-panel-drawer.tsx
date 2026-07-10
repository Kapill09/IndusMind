import { useEffect, useState } from "react";
import { X, FileSearch, ChevronDown, ChevronRight, FileText, HelpCircle } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import type { RagSource } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface SourcesPanelDrawerProps {
  sources: RagSource[] | null;
  onClose: () => void;
}

export function SourcesPanelDrawer({ sources, onClose }: SourcesPanelDrawerProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const isOpen = sources !== null && sources.length > 0;

  useEffect(() => {
    if (!isOpen) {
      setExpandedId(null);
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && sources && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-background/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Drawer panel */}
          <motion.div
            initial={{ x: "100%", boxShadow: "none" }}
            animate={{
              x: 0,
              boxShadow: "-10px 0px 30px -15px rgba(0,0,0,0.2)",
            }}
            exit={{ x: "100%", boxShadow: "none" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-card sm:max-w-lg"
            role="dialog"
            aria-modal="true"
            aria-labelledby="sources-panel-title"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <h2
                id="sources-panel-title"
                className="flex items-center gap-2 text-base font-semibold"
              >
                <FileSearch className="h-5 w-5 text-primary" aria-hidden="true" />
                Grounded Sources
                <Badge variant="outline" className="ml-1 text-muted-foreground">
                  {sources.length}
                </Badge>
              </h2>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onClose}
                aria-label="Close sources panel"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>

            {/* Source list */}
            <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-3">
              {sources.map((source) => {
                const isExpanded = expandedId === source.chunk_id;
                const filename = String(source.metadata.filename ?? "Uploaded document");
                const score = Math.max(0, Math.min(100, Math.round((source.score ?? 0.72) * 100)));
                const heading = source.metadata.heading || source.metadata.title || "Document snippet";
                const pageLabel = getPageLabel(source);

                const metadataEntries = Object.entries(source.metadata).filter(
                  ([key, val]) =>
                    val !== null &&
                    val !== undefined &&
                    key !== "filename" &&
                    key !== "page_start" &&
                    key !== "page_end",
                );

                return (
                  <div
                    key={source.chunk_id}
                    className="overflow-hidden rounded-xl border border-border bg-background transition-colors"
                  >
                    {/* Source summary row */}
                    <button
                      type="button"
                      onClick={() => setExpandedId(isExpanded ? null : source.chunk_id)}
                      className="group flex w-full items-center gap-3 p-4 text-left transition-colors hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                    >
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                        <FileText className="h-4 w-4" aria-hidden="true" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{filename}</p>
                        <div className="mt-1 flex items-center gap-2">
                          <span className="text-[11px] text-muted-foreground">{pageLabel}</span>
                          <div className="flex min-w-0 flex-1 items-center gap-1.5">
                            <Progress
                              value={score}
                              className="h-1 flex-1 bg-muted"
                            />
                            <span className="text-[11px] font-medium text-muted-foreground">
                              {score}%
                            </span>
                          </div>
                        </div>
                      </div>

                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      ) : (
                        <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      )}
                    </button>

                    {/* Expanded detail */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="border-t border-border px-4 pb-4 pt-3 space-y-4">
                            {/* Heading */}
                            <p className="text-sm font-medium text-foreground">{heading}</p>

                            {/* Retrieved text */}
                            <div className="space-y-2">
                              <h4 className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                                <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
                                Retrieved Context
                              </h4>
                              <div className="rounded-lg border border-border bg-muted/20 p-3 text-sm leading-7 text-foreground">
                                {source.text ? (
                                  <div className="whitespace-pre-wrap">{source.text}</div>
                                ) : (
                                  <p className="italic text-muted-foreground">
                                    No chunk text available.
                                  </p>
                                )}
                              </div>
                            </div>

                            {/* Metadata */}
                            {metadataEntries.length > 0 && (
                              <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-muted-foreground">
                                  Metadata
                                </h4>
                                <div className="overflow-hidden rounded-lg border border-border">
                                  <table className="w-full text-sm text-left">
                                    <tbody className="divide-y divide-border">
                                      {metadataEntries.map(([key, value]) => (
                                        <tr key={key} className="bg-card">
                                          <td className="w-1/3 border-r border-border bg-muted/10 px-3 py-1.5 text-xs font-medium capitalize text-muted-foreground">
                                            {key.replace(/_/g, " ")}
                                          </td>
                                          <td className="break-all px-3 py-1.5 font-mono text-xs text-foreground">
                                            {String(value)}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
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
