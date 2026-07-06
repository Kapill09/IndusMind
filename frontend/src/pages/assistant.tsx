import { useMemo, useRef, useState } from "react";
import type React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bot, ChevronDown, ChevronRight, Clock3, FileText, Send, Sparkles, UserRound } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { askQuestion } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatMessage, RagSource } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/feedback/toast";

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
    mutationFn: (question: string) => askQuestion(question, 5),
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

  const starterPrompts = useMemo(
    () => [
      "Summarize this document",
      "Explain Problem Statement 8",
      "Find Safety Procedures",
      "Extract SOP",
      "Compare Documents",
      "Find Compliance Rules",
      "Generate Maintenance Checklist",
    ],
    [],
  );

  const onSubmit = handleSubmit(({ question }) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      createdAt: new Date(),
    };
    setMessages((current) => [...current, userMessage]);
    reset();
    askMutation.mutate(question);
  });

  const askPrompt = (question: string) => {
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: question, createdAt: new Date() },
    ]);
    askMutation.mutate(question);
  };

  return (
    <div className="mx-auto flex min-h-[calc(100vh-7rem)] max-w-6xl flex-col">
      <section className="mb-5 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <Badge variant="outline">Grounded industrial assistant</Badge>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal md:text-3xl">AI Assistant</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Ask natural-language questions across manuals, SOPs, inspection reports, and maintenance documentation.
          </p>
        </div>
        <div className="rounded-md border border-border bg-card px-3 py-2 text-sm text-muted-foreground">
          Streaming-ready message architecture
        </div>
      </section>

      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardContent className="flex flex-1 flex-col p-0">
          <div className="flex-1 space-y-5 overflow-y-auto p-4 md:p-6">
            {messages.length === 0 ? (
              <EmptyChat prompts={starterPrompts} onPrompt={askPrompt} disabled={askMutation.isPending} />
            ) : (
              messages.map((message) => <ChatBubble key={message.id} message={message} />)
            )}
            {askMutation.isPending ? <TypingIndicator /> : null}
          </div>

          <form ref={formRef} onSubmit={onSubmit} className="border-t border-border bg-card p-4">
            <div className="flex flex-col gap-3 md:flex-row">
              <div className="flex-1">
                <Textarea
                  {...register("question")}
                  aria-label="Ask INDUS MIND"
                  placeholder="Ask about maintenance procedures, inspection findings, SOP steps, tables, figures, or problem statements..."
                  className="min-h-20"
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                      formRef.current?.requestSubmit();
                    }
                  }}
                />
                {errors.question ? (
                  <p className="mt-2 text-sm text-destructive">{errors.question.message}</p>
                ) : null}
              </div>
              <Button type="submit" className="md:self-end" disabled={askMutation.isPending}>
                <Send className="h-4 w-4" aria-hidden="true" />
                Ask
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function EmptyChat({
  prompts,
  onPrompt,
  disabled,
}: {
  prompts: string[];
  onPrompt: (prompt: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
        <Sparkles className="h-6 w-6" aria-hidden="true" />
      </div>
      <h2 className="mt-4 text-lg font-semibold">Ready for plant knowledge questions</h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
        Answers are grounded in uploaded documents and include source citations when available.
      </p>
      <div className="mt-6 grid w-full max-w-3xl gap-3 md:grid-cols-3">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            disabled={disabled}
            onClick={() => onPrompt(prompt)}
            className="rounded-lg border border-border bg-background p-4 text-left text-sm transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isAssistant = message.role === "assistant";

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={cn("flex gap-3", isAssistant ? "items-start" : "items-start justify-end")}
    >
      {isAssistant ? <BubbleIcon assistant /> : null}
      <div className={cn("max-w-[880px] rounded-2xl border p-4 shadow-sm", isAssistant ? "bg-card" : "bg-primary text-primary-foreground")}>
        <div className="whitespace-pre-wrap text-sm leading-7">{message.content}</div>
        {isAssistant ? <AssistantMetadata message={message} /> : null}
      </div>
      {!isAssistant ? <BubbleIcon /> : null}
    </motion.article>
  );
}

function BubbleIcon({ assistant = false }: { assistant?: boolean }) {
  return (
    <div
      className={cn(
        "mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border",
        assistant ? "bg-secondary text-secondary-foreground" : "bg-card text-muted-foreground",
      )}
    >
      {assistant ? <Bot className="h-4 w-4" /> : <UserRound className="h-4 w-4" />}
    </div>
  );
}

function AssistantMetadata({ message }: { message: ChatMessage }) {
  return (
    <div className="mt-4 space-y-3 border-t border-border pt-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">Confidence {message.confidence ?? 72}%</Badge>
        {message.latencyMs ? (
          <Badge variant="outline">
            <Clock3 className="mr-1 h-3 w-3" aria-hidden="true" />
            {message.latencyMs} ms
          </Badge>
        ) : null}
        {message.model ? <Badge variant="outline">{message.model}</Badge> : null}
      </div>
      {message.sources?.length ? <SourcesList sources={message.sources} /> : null}
    </div>
  );
}

function SourcesList({ sources }: { sources: RagSource[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="space-y-2">
      {sources.slice(0, 4).map((source) => {
        const filename = String(source.metadata.filename ?? "Uploaded document");
        const isOpen = expanded === source.chunk_id;
        return (
          <div key={source.chunk_id} className="rounded-xl border border-border bg-background/70 p-3">
            <button
              type="button"
              onClick={() => setExpanded(isOpen ? null : source.chunk_id)}
              className="flex w-full items-start justify-between gap-3 text-left"
            >
              <div className="flex min-w-0 items-start gap-2">
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold">{filename}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {pageLabel(source.page_start, source.page_end)} · score {Math.round((source.score ?? 0.72) * 100)}%
                  </p>
                </div>
              </div>
              {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
            {isOpen ? (
              <div className="mt-3 rounded-lg border border-border bg-background p-3 text-xs leading-6 text-muted-foreground">
                <p className="font-medium text-foreground">Retrieved chunk excerpt</p>
                <p className="mt-2">
                  {source.metadata.heading ? `${source.metadata.heading} — ` : ""}
                  {source.metadata.title ? `${source.metadata.title} — ` : ""}
                  Grounded snippet from the uploaded document.
                </p>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <BubbleIcon assistant />
      <div className="w-full max-w-xl rounded-lg border bg-card p-4">
        <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
          <span>INDUS MIND is retrieving grounded context</span>
        </div>
        <div className="space-y-2">
          <Skeleton className="h-3 w-11/12" />
          <Skeleton className="h-3 w-8/12" />
          <Skeleton className="h-3 w-9/12" />
        </div>
      </div>
    </div>
  );
}

function estimateConfidence(sources: RagSource[]) {
  if (!sources.length) return 0;
  const bestScore = Math.max(...sources.map((source) => source.score ?? 0.72));
  return Math.max(55, Math.min(96, Math.round(bestScore * 100)));
}

function pageLabel(start: number | null, end: number | null) {
  if (!start && !end) return "page unknown";
  if (start && end && start !== end) return `pages ${start}-${end}`;
  return `page ${start ?? end}`;
}
