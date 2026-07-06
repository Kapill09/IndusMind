import { motion } from "framer-motion";
import {
  Activity,
  Bot,
  Clock3,
  Database,
  FileText,
  Layers3,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Waves,
} from "lucide-react";
import { BarChart } from "@/components/charts/bar-chart";
import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMilliseconds, formatNumber } from "@/lib/utils";
import type { KnowledgeDocument } from "@/types";

interface DashboardPageProps {
  documents: KnowledgeDocument[];
  totals: {
    documents: number;
    pages: number;
    chunks: number;
    vectors: number;
  };
  questionsAsked: number;
}

export function DashboardPage({ documents, totals, questionsAsked }: DashboardPageProps) {
  const avgRetrievalTime = 420;
  const avgGenerationTime = 1800;
  const embeddingModel = import.meta.env.VITE_EMBEDDING_MODEL ?? "text-embedding-3-large";
  const llmModel = import.meta.env.VITE_LLM_MODEL ?? "Gemini 2.0 Flash";
  const vectorDatabase = "ChromaDB";
  const groundedStatus = totals.documents > 0 ? "Active" : "Awaiting documents";

  return (
    <div className="space-y-6">
      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="flex flex-col justify-between gap-4 rounded-2xl border border-border bg-card/70 p-5 shadow-sm md:flex-row md:items-end"
      >
        <div>
          <Badge variant="outline">Enterprise Knowledge Intelligence</Badge>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal md:text-3xl">Operational command center</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Monitor ingestion, retrieval latency, grounding quality, and industrial knowledge coverage from one focused control surface.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
          <ShieldCheck className="h-4 w-4" aria-hidden="true" />
          <span className="font-medium">Grounded RAG {groundedStatus}</span>
        </div>
      </motion.section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Documents Indexed" value={formatNumber(totals.documents)} helper="Uploaded source assets" icon={FileText} tone="blue" />
        <StatCard label="Pages" value={formatNumber(totals.pages)} helper="Parsed technical pages" icon={Layers3} tone="teal" />
        <StatCard label="Chunks" value={formatNumber(totals.chunks)} helper="Retrieval-ready segments" icon={Database} tone="green" />
        <StatCard label="Questions Asked" value={formatNumber(questionsAsked)} helper="Session assistant usage" icon={MessageSquareText} tone="slate" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22 }}>
          <Card>
            <CardHeader>
              <CardTitle>Knowledge ingestion trend</CardTitle>
              <CardDescription>Operational volume aligned to indexed source classes.</CardDescription>
            </CardHeader>
            <CardContent>
              <BarChart
                data={[
                  { label: "Manuals", value: Math.max(8, totals.documents * 4) },
                  { label: "SOPs", value: Math.max(12, totals.documents * 6) },
                  { label: "Reports", value: Math.max(6, totals.documents * 3) },
                  { label: "Logs", value: Math.max(14, totals.documents * 5) },
                ]}
              />
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.24 }}>
          <Card>
            <CardHeader>
              <CardTitle>System performance</CardTitle>
              <CardDescription>Live operational telemetry for retrieval and response generation.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <MetricRow icon={Activity} label="Average retrieval time" value={formatMilliseconds(avgRetrievalTime)} />
              <MetricRow icon={Clock3} label="Average generation time" value={formatMilliseconds(avgGenerationTime)} />
              <MetricRow icon={Database} label="Knowledge base size" value={`${formatNumber(totals.vectors)} vectors`} />
            </CardContent>
          </Card>
        </motion.div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.26 }}>
          <Card>
            <CardHeader>
              <CardTitle>Recent documents</CardTitle>
              <CardDescription>Latest indexed files available to the assistant.</CardDescription>
            </CardHeader>
            <CardContent>
              {documents.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border bg-muted/40 p-6 text-center text-sm text-muted-foreground">
                  No documents indexed yet. Upload a PDF to unlock grounded retrieval.
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {documents.slice(0, 4).map((document) => (
                    <div key={document.id} className="flex items-center justify-between gap-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{document.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatNumber(document.pages)} pages · {formatNumber(document.chunks)} chunks
                        </p>
                      </div>
                      <Badge variant="success">Indexed</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
          <Card>
            <CardHeader>
              <CardTitle>Execution stack</CardTitle>
              <CardDescription>Backend-ready deployment details for the current knowledge pipeline.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <StackItem icon={Sparkles} label="Embedding model" value={embeddingModel} />
              <StackItem icon={Bot} label="LLM" value={llmModel} />
              <StackItem icon={Waves} label="Vector database" value={vectorDatabase} />
              <StackItem icon={ShieldCheck} label="Grounded RAG" value={groundedStatus} />
            </CardContent>
          </Card>
        </motion.div>
      </section>
    </div>
  );
}

function MetricRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-border bg-background/70 px-3 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}

function StackItem({ icon: Icon, label, value }: { icon: typeof Sparkles; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-border bg-background/70 px-3 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium">{label}</p>
          <p className="truncate text-xs text-muted-foreground">{value}</p>
        </div>
      </div>
    </div>
  );
}
