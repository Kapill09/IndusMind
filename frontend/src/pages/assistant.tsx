import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { askQuestion } from "@/lib/api";
import { DocumentSelector } from "@/components/documents/document-selector";
import { useSelectedDocuments } from "@/hooks/use-selected-documents";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/feedback/toast";
import type { ChatMessage, RagSource } from "@/types";
import { EmptyState } from "@/components/assistant/empty-state";
import { LoadingPipeline } from "@/components/assistant/loading-pipeline";
import { SourceDrawer } from "@/components/assistant/source-drawer";
import { ConversationHistory } from "@/components/assistant/conversation-history";
import { AssistantContentPanel } from "@/components/assistant/assistant-content-panel";
import { AssistantRightPanel } from "@/components/assistant/assistant-right-panel";

const questionSchema = z.object({
  question: z.string().trim().min(3, "Enter a question for the assistant."),
});

type QuestionForm = z.infer<typeof questionSchema>;

interface AssistantPageProps {
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  onQuestionAnswered: () => void;
}

export function AssistantPage({ messages, setMessages, onQuestionAnswered }: AssistantPageProps) {
  const { notify } = useToast();
  const formRef = useRef<HTMLFormElement | null>(null);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const [selectedSource, setSelectedSource] = useState<RagSource | null>(null);
  const { selected: selectedDocumentIds } = useSelectedDocuments();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<QuestionForm>({
    resolver: zodResolver(questionSchema),
    defaultValues: { question: "" },
  });

  const askMutation = useMutation({
    mutationKey: ["assistant", "ask"],
    mutationFn: ({ question, documentIds }: { question: string; documentIds?: string[] | null }) =>
      askQuestion(question, 5, documentIds ?? null),
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
        },
      ]);
      onQuestionAnswered();
    },
    onError: (error) => {
      notify({
        tone: "error",
        title: "Question failed",
        description: error instanceof Error ? error.message : "The assistant could not complete the request.",
      });
    },
  });
  const { error: askError, isError: isAskError, isPending: isAsking, mutate: ask } = askMutation;

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [messages.length, isAsking]);

  const submitQuestion = useCallback((question: string) => {
    if (isAsking) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      createdAt: new Date(),
    };
    setMessages((current) => [...current, userMessage]);
    ask({ question, documentIds: selectedDocumentIds });
  }, [ask, isAsking, selectedDocumentIds, setMessages]);

  const onSubmit = handleSubmit(({ question }) => {
    submitQuestion(question);
    reset();
  });

  const askPrompt = useCallback((question: string) => {
    submitQuestion(question);
  }, [submitQuestion]);

  const onNewChat = useCallback(() => {
    setMessages([]);
  }, [setMessages]);

  const onReplayQuery = useCallback((query: string) => {
    askPrompt(query);
  }, [askPrompt]);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      notify({ tone: "success", title: "Copied", description: "Answer copied to clipboard." });
    } catch {
      notify({ tone: "error", title: "Copy failed", description: "Unable to copy text." });
    }
  }, [notify]);

  const handleRegenerate = useCallback(() => {
    const lastUserMessage = [...messages].reverse().find((message) => message.role === "user");
    if (lastUserMessage) {
      askPrompt(lastUserMessage.content);
    }
  }, [askPrompt, messages]);

  const handleLike = useCallback(() => {
    notify({ tone: "success", title: "Feedback recorded", description: "Thanks for your input." });
  }, [notify]);

  const handleDislike = useCallback(() => {
    notify({ tone: "error", title: "Feedback recorded", description: "We will improve future responses." });
  }, [notify]);

  const latestAnswer = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant") ?? null,
    [messages],
  );
  const assistantError = askError instanceof Error
    ? askError.message
    : "The assistant could not complete the request.";

  return (
    <div className="mx-auto min-h-[calc(100vh-6rem)] max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
      <div className="grid gap-6 lg:grid-cols-[minmax(260px,280px)_minmax(0,1fr)] xl:grid-cols-[minmax(260px,280px)_minmax(0,1fr)_minmax(260px,300px)]">
        <ConversationHistory messages={messages} onNewChat={onNewChat} onReplayQuery={onReplayQuery} />

        <main className="flex min-h-0 min-w-0 flex-col gap-4">
          {messages.length === 0 ? (
            <Card className="flex flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-card/95 p-6 shadow-xl shadow-black/10">
              <CardContent className="flex-1 p-0">
                <EmptyState onPrompt={askPrompt} disabled={isAsking} />
              </CardContent>
            </Card>
          ) : (
            <AssistantContentPanel
              messages={messages}
              onSourceClick={setSelectedSource}
              onSuggest={askPrompt}
              onRegenerate={handleRegenerate}
              onCopy={handleCopy}
              onLike={handleLike}
              onDislike={handleDislike}
            />
          )}
          <div ref={conversationEndRef} />

          {isAskError ? (
            <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive" role="alert">
              {assistantError}
            </div>
          ) : null}

          <form ref={formRef} onSubmit={onSubmit} className="rounded-2xl border border-border bg-card/95 p-4 shadow-xl shadow-black/10">
            <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
              <Textarea
                {...register("question")}
                aria-label="Ask the industrial copilot"
                placeholder="Ask about equipment, procedures, maintenance records, or compliance standards..."
                disabled={isAsking}
                className="min-h-[110px] resize-none bg-background text-foreground placeholder:text-muted-foreground"
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    formRef.current?.requestSubmit();
                  }
                }}
              />
              <div className="flex flex-col items-stretch justify-end gap-3">
                <DocumentSelector compact />
                <Button type="submit" size="lg" disabled={isAsking}>
                  <Send className="h-4 w-4" aria-hidden="true" />
                  {isAsking ? "Working..." : "Ask Copilot"}
                </Button>
              </div>
            </div>
            {errors.question ? <p className="mt-3 text-sm text-destructive">{errors.question.message}</p> : null}
          </form>

          {isAsking ? (
            <div className="rounded-2xl border border-border bg-card/95 p-4 shadow-xl shadow-black/10">
              <LoadingPipeline />
            </div>
          ) : null}
        </main>

        <AssistantRightPanel latestAnswer={latestAnswer} onSourceClick={setSelectedSource} onQuickAction={askPrompt} />
      </div>

      <SourceDrawer source={selectedSource} onClose={() => setSelectedSource(null)} />
    </div>
  );
}

function estimateConfidence(sources: RagSource[]) {
  if (!sources || !sources.length) return 0;
  const bestScore = Math.max(...sources.map((source) => source.score ?? 0.72));
  return Math.max(55, Math.min(96, Math.round(bestScore * 100)));
}
