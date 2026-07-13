import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { askQuestion } from "@/lib/api";
import { useSelectedDocuments } from "@/hooks/use-selected-documents";
import { useToast } from "@/components/feedback/toast";
import type { ChatMessage, PageKey, RagSource } from "@/types";
import { EmptyState } from "@/components/assistant/empty-state";
import { LoadingPipeline } from "@/components/assistant/loading-pipeline";
import { AssistantTopBar } from "@/components/assistant/assistant-top-bar";
import { ChatInput } from "@/components/assistant/chat-input";
import { UserMessage } from "@/components/assistant/user-message";
import { AssistantMessage } from "@/components/assistant/assistant-message";
import { SourcesPanelDrawer } from "@/components/assistant/sources-panel-drawer";
import { SourcePdfViewerDrawer } from "@/components/assistant/source-pdf-viewer-drawer";

interface AssistantPageProps {
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  onQuestionAnswered: () => void;
  onNavigate: (page: PageKey) => void;
}

export function AssistantPage({
  messages,
  setMessages,
  onQuestionAnswered,
  onNavigate,
}: AssistantPageProps) {
  const { notify } = useToast();
  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const [drawerSources, setDrawerSources] = useState<RagSource[] | null>(null);
  const [activePdfSource, setActivePdfSource] = useState<RagSource | null>(null);
  const [activePdfSources, setActivePdfSources] = useState<RagSource[]>([]);
  const [activePdfConfidence, setActivePdfConfidence] = useState<number | undefined>();
  const { selected: selectedDocumentIds } = useSelectedDocuments();

  // ── Mutation ──
  const askMutation = useMutation({
    mutationKey: ["assistant", "ask"],
    mutationFn: ({
      question,
      documentIds,
    }: {
      question: string;
      documentIds?: string[] | null;
    }) => askQuestion(question, 5, documentIds ?? null),
    onSuccess: (response) => {
      const confidence = estimateConfidence(response.sources);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          createdAt: new Date(),
          sources: response.sources,
          confidence,
          latencyMs: response.retrieval_time_ms,
          model: response.model,
          entities: response.entities,
          contextChunks: response.context_chunks,
          retrievalScope: response.retrieval_scope,
        },
      ]);
      onQuestionAnswered();
    },
    onError: (error) => {
      notify({
        tone: "error",
        title: "Question failed",
        description:
          error instanceof Error
            ? error.message
            : "The assistant could not complete the request.",
      });
    },
  });

  const {
    error: askError,
    isError: isAskError,
    isPending: isAsking,
    mutate: ask,
  } = askMutation;

  // ── Auto-scroll ──
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({
      block: "end",
      behavior: "smooth",
    });
  }, [messages.length, isAsking]);

  // ── Handlers ──
  const submitQuestion = useCallback(
    (question: string) => {
      if (isAsking) return;
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: question,
        createdAt: new Date(),
      };
      setMessages((current) => [...current, userMessage]);
      ask({ question, documentIds: selectedDocumentIds });
    },
    [ask, isAsking, selectedDocumentIds, setMessages],
  );

  const onNewChat = useCallback(() => {
    setMessages([]);
  }, [setMessages]);

  const onReplayQuery = useCallback(
    (query: string) => {
      submitQuestion(query);
    },
    [submitQuestion],
  );

  const handleCopy = useCallback(
    async (text: string) => {
      try {
        await navigator.clipboard.writeText(text);
        notify({
          tone: "success",
          title: "Copied",
          description: "Answer copied to clipboard.",
        });
      } catch {
        notify({
          tone: "error",
          title: "Copy failed",
          description: "Unable to copy text.",
        });
      }
    },
    [notify],
  );

  const handleRegenerate = useCallback(() => {
    const lastUserMessage = [...messages]
      .reverse()
      .find((message) => message.role === "user");
    if (lastUserMessage) {
      submitQuestion(lastUserMessage.content);
    }
  }, [submitQuestion, messages]);

  const handleLike = useCallback(() => {
    notify({
      tone: "success",
      title: "Feedback recorded",
      description: "Thanks for your input.",
    });
  }, [notify]);

  const handleDislike = useCallback(() => {
    notify({
      tone: "error",
      title: "Feedback recorded",
      description: "We will improve future responses.",
    });
  }, [notify]);

  const handleViewSources = useCallback((sources: RagSource[]) => {
    setDrawerSources(sources);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setDrawerSources(null);
  }, []);

  const handleSourceClick = useCallback(
    (source: RagSource, contextSources?: RagSource[], confidenceScore?: number) => {
      setActivePdfSource(source);
      setActivePdfSources(contextSources ?? [source]);
      setActivePdfConfidence(confidenceScore);
    },
    [],
  );

  const handleClosePdfViewer = useCallback(() => {
    setActivePdfSource(null);
    setActivePdfSources([]);
    setActivePdfConfidence(undefined);
  }, []);

  const handleOpenKnowledgeGraph = useCallback(() => {
    onNavigate("knowledge-graph");
  }, [onNavigate]);

  const assistantError =
    isAskError && askError
      ? askError instanceof Error
        ? askError.message
        : "The assistant could not complete the request."
      : null;

  // ── Render ──
  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col overflow-hidden -mx-4 -my-5 sm:-mx-6 sm:-my-6 lg:-mx-8 lg:-my-8">
      {/* Top bar */}
      <AssistantTopBar
        messages={messages}
        onNewChat={onNewChat}
        onReplayQuery={onReplayQuery}
      />

      {/* Chat area — scrollable center column */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-[1080px] px-4 py-6">
          {messages.length === 0 ? (
            <EmptyState onPrompt={submitQuestion} disabled={isAsking} />
          ) : (
            <div className="space-y-6" aria-live="polite">
              {messages.map((message) =>
                message.role === "user" ? (
                  <UserMessage key={message.id} content={message.content} />
                ) : (
                  <AssistantMessage
                    key={message.id}
                    message={message}
                    onSourceClick={handleSourceClick}
                    onViewSources={handleViewSources}
                    onSuggest={submitQuestion}
                    onRegenerate={handleRegenerate}
                    onCopy={handleCopy}
                    onLike={handleLike}
                    onDislike={handleDislike}
                    onOpenKnowledgeGraph={handleOpenKnowledgeGraph}
                  />
                ),
              )}

              {/* Loading indicator */}
              {isAsking && (
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-card text-primary shadow-sm">
                    <div className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <LoadingPipeline />
                  </div>
                </div>
              )}

              <div ref={conversationEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Sticky input */}
      <ChatInput
        onSubmit={submitQuestion}
        isLoading={isAsking}
        error={assistantError}
      />

      {/* Sources drawer */}
      <SourcesPanelDrawer
        sources={drawerSources}
        onClose={handleCloseDrawer}
      />
      <SourcePdfViewerDrawer
        source={activePdfSource}
        sources={activePdfSources}
        confidenceScore={activePdfConfidence}
        onClose={handleClosePdfViewer}
        onOpenKnowledgeGraph={handleOpenKnowledgeGraph}
      />
    </div>
  );
}

function estimateConfidence(sources: RagSource[]) {
  if (!sources || !sources.length) return 0;
  const bestScore = Math.max(
    ...sources.map((source) => source.score ?? 0.72),
  );
  return Math.max(55, Math.min(96, Math.round(bestScore * 100)));
}
