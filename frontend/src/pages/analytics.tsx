import { BarChart3, Database, FileStack, Gauge, Layers3, Timer } from "lucide-react";
import { BarChart } from "@/components/charts/bar-chart";
import { StatCard } from "@/components/dashboard/stat-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMilliseconds, formatNumber } from "@/lib/utils";

interface AnalyticsPageProps {
  totals: {
    documents: number;
    pages: number;
    chunks: number;
    vectors: number;
  };
  questionsAsked: number;
}

export function AnalyticsPage({ totals, questionsAsked }: AnalyticsPageProps) {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal md:text-3xl">Analytics</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          Operational telemetry view for retrieval quality, document coverage, and knowledge base growth.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Documents" value={formatNumber(totals.documents)} helper="Indexed sources" icon={FileStack} tone="blue" />
        <StatCard label="Pages" value={formatNumber(totals.pages)} helper="Parsed pages" icon={Layers3} tone="teal" />
        <StatCard label="Chunks" value={formatNumber(totals.chunks)} helper="Retrieval units" icon={Database} tone="green" />
        <StatCard label="Questions Asked" value={formatNumber(questionsAsked)} helper="Current browser session" icon={BarChart3} tone="slate" />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Retrieval performance</CardTitle>
            <CardDescription>Placeholder data for retrieval and generation latency.</CardDescription>
          </CardHeader>
          <CardContent>
            <BarChart
              data={[
                { label: "Semantic", value: 410 },
                { label: "Keyword", value: 180 },
                { label: "Structured", value: 95 },
                { label: "Gemini", value: 1780 },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Knowledge coverage</CardTitle>
            <CardDescription>Placeholder category distribution across industrial document classes.</CardDescription>
          </CardHeader>
          <CardContent>
            <BarChart
              data={[
                { label: "Maintenance", value: 72 },
                { label: "Safety", value: 54 },
                { label: "Inspection", value: 46 },
                { label: "Operations", value: 63 },
              ]}
            />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricPanel icon={Gauge} label="Average Retrieval Time" value={formatMilliseconds(420)} />
        <MetricPanel icon={Timer} label="Average Generation Time" value={formatMilliseconds(1800)} />
        <MetricPanel icon={Database} label="Knowledge Base Size" value={`${formatNumber(totals.vectors)} vectors`} />
      </section>
    </div>
  );
}

function MetricPanel({ icon: Icon, label, value }: { icon: typeof Gauge; label: string; value: string }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-1 text-lg font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
