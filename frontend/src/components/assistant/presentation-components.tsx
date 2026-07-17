import { MarkdownContent } from "./markdown-content";
import { CheckCircle2, GitBranch, LayoutGrid, List } from "lucide-react";

interface PresentationComponentProps {
  title: string;
  content: string;
}

export function DataMatrix({ title, content }: PresentationComponentProps) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2 border-b border-border/40 pb-3">
        <LayoutGrid className="h-4 w-4 text-primary" />
        <h3 className="text-[13px] font-bold uppercase tracking-[0.16em] text-foreground">{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <MarkdownContent content={content} className="max-w-none text-sm" />
      </div>
    </div>
  );
}

export function WorkflowTimeline({ title, content }: PresentationComponentProps) {
  return (
    <div className="rounded-2xl border border-primary/20 bg-primary/5 p-5">
      <div className="mb-4 flex items-center gap-2 border-b border-primary/20 pb-3">
        <GitBranch className="h-4 w-4 text-primary" />
        <h3 className="text-[13px] font-bold uppercase tracking-[0.16em] text-primary">{title}</h3>
      </div>
      <MarkdownContent content={content} className="max-w-none text-sm prose-ol:pl-4 prose-li:mb-2 prose-li:marker:text-primary prose-li:marker:font-semibold" />
    </div>
  );
}

export function BulletList({ title, content }: PresentationComponentProps) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/80 p-5">
      <div className="mb-3 flex items-center gap-2">
        <List className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-[13px] font-bold uppercase tracking-[0.16em] text-muted-foreground">{title}</h3>
      </div>
      <MarkdownContent content={content} className="max-w-none text-sm prose-ul:pl-4 prose-li:marker:text-muted-foreground" />
    </div>
  );
}

export function SummaryCard({ title, content }: PresentationComponentProps) {
  return (
    <div className="rounded-2xl bg-muted/30 p-5 text-foreground border border-border/50">
      <div className="mb-3 flex items-center gap-2">
        <CheckCircle2 className="h-4 w-4 text-primary" />
        <h3 className="text-[13px] font-bold uppercase tracking-[0.16em] text-foreground">{title}</h3>
      </div>
      <div className="text-[14.5px] leading-relaxed opacity-90">
        <MarkdownContent content={content} className="max-w-none" />
      </div>
    </div>
  );
}

export function ArchitectureCard({ title, content }: PresentationComponentProps) {
  return (
    <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-5 shadow-sm">
      <h3 className="mb-4 text-[13px] font-bold uppercase tracking-[0.16em] text-blue-500">{title}</h3>
      <div className="text-sm leading-relaxed">
        <MarkdownContent content={content} className="max-w-none prose-p:font-mono" />
      </div>
    </div>
  );
}
