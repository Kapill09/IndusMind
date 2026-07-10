import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div
      className={cn(
        "prose prose-sm prose-pre:bg-slate-950 prose-pre:text-slate-100 prose-code:rounded-md prose-code:border prose-code:border-border prose-code:px-2 prose-code:py-1 prose-blockquote:border-l prose-blockquote:border-muted prose-blockquote:bg-muted/20 prose-blockquote:text-muted-foreground prose-table:border prose-table:border-border prose-table:bg-card prose-table:text-sm prose-table:shadow-sm dark:prose-invert",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
