import { useState, useCallback } from "react";
import { Plus, Clock, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConversationHistoryPopover } from "@/components/assistant/conversation-history-popover";
import type { ChatMessage } from "@/types";

interface AssistantTopBarProps {
  messages: ChatMessage[];
  onNewChat: () => void;
  onReplayQuery: (query: string) => void;
}

export function AssistantTopBar({ messages, onNewChat, onReplayQuery }: AssistantTopBarProps) {
  const [historyOpen, setHistoryOpen] = useState(false);

  const handleClose = useCallback(() => setHistoryOpen(false), []);

  return (
    <div className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-12 max-w-[820px] items-center justify-between gap-3 px-4">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold text-foreground">AI Assistant</h1>
          <span className="hidden rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary sm:inline-block">
            RAG-Powered
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setHistoryOpen(!historyOpen)}
              className="h-8 gap-1.5 px-2.5 text-xs text-muted-foreground hover:text-foreground"
              aria-label="Conversation history"
            >
              <Clock className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">History</span>
            </Button>
            <ConversationHistoryPopover
              messages={messages}
              onReplayQuery={onReplayQuery}
              isOpen={historyOpen}
              onClose={handleClose}
            />
          </div>

          <div className="h-5 w-px bg-border" />

          <Button
            variant="ghost"
            size="sm"
            onClick={onNewChat}
            className="h-8 gap-1.5 px-2.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            New Chat
          </Button>
        </div>
      </div>
    </div>
  );
}
