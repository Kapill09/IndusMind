import { Activity, Clock3, Database, FileText, Layers3, MessageSquareText, ShieldCheck } from "lucide-react";
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

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <Badge variant="outline">Enterprise Knowledge Intelligence</Badge>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal md:text-3xl">Operational command center</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Monitor document ingestion, retrieval performance, and industrial knowledge coverage from one focused console.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm">
          <ShieldCheck className="h-4 w-4 text-emerald-600" aria-hidden="true" />
          <span className="font-medium">Grounded RAG active</span>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Documents" value={formatNumber(totals.documents)} helper="Indexed PDF assets" icon={FileText} tone="blue" />
        <StatCard label="Pages" value={formatNumber(totals.pages)} helper="Parsed technical pages" icon={Layers3} tone="teal" />
        <StatCard label="Chunks" value={formatNumber(totals.chunks)} helper="Retrieval-ready segments" icon={Database} tone="green" />
        <StatCard label="Questions Asked" value={formatNumber(questionsAsked)} helper="Session assistant usage" icon={MessageSquareText} tone="slate" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Knowledge ingestion trend</CardTitle>
            <CardDescription>Placeholder operational trend for uploaded knowledge volume.</CardDescription>
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

        <Card>
          <CardHeader>
            <CardTitle>System performance</CardTitle>
            <CardDescription>Current session and placeholder generation metrics.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <MetricRow icon={Activity} label="Average retrieval time" value={formatMilliseconds(avgRetrievalTime)} />
            <MetricRow icon={Clock3} label="Average generation time" value={formatMilliseconds(avgGenerationTime)} />
            <MetricRow icon={Database} label="Knowledge base size" value={`${formatNumber(totals.vectors)} vectors`} />
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Recent documents</CardTitle>
          <CardDescription>Latest indexed files available to the assistant.</CardDescription>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>
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
    <div className="flex items-center justify-between gap-4 rounded-md border border-border p-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}
