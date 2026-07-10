import { memo, useMemo, useState, useRef, useEffect } from "react";
import { Clock, Search, X, Pin, ChevronRight } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ChatMessage } from "@/types";

interface ConversationHistoryPopoverProps {
  messages: ChatMessage[];
  onReplayQuery: (query: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const ConversationHistoryPopover = memo(function ConversationHistoryPopover({
  messages,
  onReplayQuery,
  isOpen,
  onClose,
}: ConversationHistoryPopoverProps) {
  const [searchValue, setSearchValue] = useState("");
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const normalizedSearch = searchValue.trim().toLowerCase();

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onClose]);

  const groupedQueries = useMemo(() => {
    const userMessages = messages
      .filter((m) => m.role === "user")
      .slice()
      .reverse();

    // Deduplicate
    const unique = new Map<string, ChatMessage>();
    for (const msg of userMessages) {
      if (!unique.has(msg.content)) unique.set(msg.content, msg);
    }

    const all = Array.from(unique.values()).filter((m) =>
      m.content.toLowerCase().includes(normalizedSearch),
    );

    // Group by date
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const yesterday = today - 86400000;

    const groups: { label: string; items: ChatMessage[] }[] = [
      { label: "Today", items: [] },
      { label: "Yesterday", items: [] },
      { label: "Previous", items: [] },
    ];

    for (const msg of all) {
      const ts = new Date(msg.createdAt).getTime();
      if (ts >= today) groups[0].items.push(msg);
      else if (ts >= yesterday) groups[1].items.push(msg);
      else groups[2].items.push(msg);
    }

    return groups.filter((g) => g.items.length > 0);
  }, [messages, normalizedSearch]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={popoverRef}
          initial={{ opacity: 0, scale: 0.95, y: -8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -8 }}
          transition={{ duration: 0.18 }}
          className="absolute left-0 top-full z-50 mt-2 w-[380px] max-h-[480px] overflow-hidden rounded-2xl border border-border bg-card shadow-xl shadow-black/15"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Clock className="h-4 w-4 text-primary" aria-hidden="true" />
              Conversation History
            </div>
            <Button variant="ghost" size="sm" onClick={onClose} className="h-7 w-7 p-0">
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          </div>

          {/* Search */}
          <div className="border-b border-border px-4 py-2.5">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                placeholder="Search conversations..."
                className="h-8 bg-muted/30 pl-8 text-xs"
                aria-label="Search conversation history"
              />
            </div>
          </div>

          {/* Conversation list */}
          <div className="max-h-[360px] overflow-y-auto scrollbar-thin p-2">
            {groupedQueries.length === 0 ? (
              <div className="px-3 py-8 text-center text-sm text-muted-foreground">
                {searchValue ? "No conversations match your search." : "No conversations yet. Ask a question to get started."}
              </div>
            ) : (
              groupedQueries.map((group) => (
                <div key={group.label} className="mb-2 last:mb-0">
                  <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                    {group.label}
                  </p>
                  {group.items.slice(0, 6).map((msg) => (
                    <button
                      key={msg.id}
                      type="button"
                      onClick={() => {
                        onReplayQuery(msg.content);
                        onClose();
                      }}
                      className="group flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm text-foreground">{msg.content}</p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          {new Date(msg.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </p>
                      </div>
                      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground/50 transition group-hover:text-primary" aria-hidden="true" />
                    </button>
                  ))}
                </div>
              ))
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
