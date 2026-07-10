import { memo, useMemo, useState } from "react";
import { Clock3, Plus, Search, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import type { ChatMessage } from "@/types";

interface ConversationHistoryProps {
  messages: ChatMessage[];
  onNewChat: () => void;
  onReplayQuery: (query: string) => void;
}

export const ConversationHistory = memo(function ConversationHistory({ messages, onNewChat, onReplayQuery }: ConversationHistoryProps) {
  const [searchValue, setSearchValue] = useState("");
  const normalizedSearch = searchValue.trim().toLowerCase();

  const queries = useMemo(() => {
    const items = messages
      .filter((message) => message.role === "user")
      .slice()
      .reverse();

    const unique = new Map<string, ChatMessage>();
    for (const message of items) {
      if (!unique.has(message.content)) {
        unique.set(message.content, message);
      }
    }

    return Array.from(unique.values()).filter((message) => message.content.toLowerCase().includes(normalizedSearch));
  }, [messages, normalizedSearch]);

  return (
    <aside className="flex min-h-0 flex-col gap-4 rounded-2xl border border-border bg-card/95 p-4 shadow-xl shadow-black/10 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Workspace</p>
          <h2 className="mt-2 text-xl font-semibold text-foreground">Conversation Hub</h2>
        </div>
        <Button variant="secondary" size="sm" onClick={onNewChat}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          New Chat
        </Button>
      </div>

      <div className="space-y-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            value={searchValue}
            onChange={(event) => setSearchValue(event.target.value)}
            placeholder="Search conversations"
            aria-label="Search previous queries"
            className="bg-background pl-9"
          />
        </div>
        <div className="rounded-2xl border border-border bg-muted/20 p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Recent queries</p>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
              {queries.length}
            </span>
          </div>

          <div className="mt-3 space-y-2">
            {queries.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-background p-4 text-sm text-muted-foreground">
                {searchValue ? "No previous queries match your search." : "Ask a question to start a conversation."}
              </div>
            ) : (
              queries.slice(0, 8).map((message) => (
                <button
                  key={message.id}
                  type="button"
                  onClick={() => onReplayQuery(message.content)}
                  className="group flex w-full items-center justify-between gap-3 rounded-2xl border border-border bg-background p-3 text-left transition hover:border-primary hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{message.content}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{new Date(message.createdAt).toLocaleDateString()}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition group-hover:text-primary" aria-hidden="true" />
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      <Card className="mt-auto border-border bg-muted/20 text-muted-foreground shadow-none">
        <div className="space-y-3 p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock3 className="h-4 w-4 text-primary" aria-hidden="true" />
            <span className="text-xs font-semibold uppercase tracking-[0.18em]">Efficiency signal</span>
          </div>
          <p className="text-sm leading-6">
            Reuse previous queries to keep operational follow-up work moving without rebuilding context manually.
          </p>
        </div>
      </Card>
    </aside>
  );
});
