import { BarChart3, Database, FileStack, Gauge, Timer } from "lucide-react";
import { ResponsiveContainer, BarChart as RechartsBarChart, CartesianGrid, Cell, Line, LineChart, Tooltip, XAxis, YAxis, Bar } from "recharts";
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
  const queryTrend = [
    { day: "Mon", queries: 14 },
    { day: "Tue", queries: 22 },
    { day: "Wed", queries: 18 },
    { day: "Thu", queries: 31 },
    { day: "Fri", queries: 27 },
  ];

  const documentMix = [
    { name: "Maintenance", value: 72 },
    { name: "Safety", value: 54 },
    { name: "Inspection", value: 46 },
    { name: "Operations", value: 63 },
  ];

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-[-0.02em] md:text-3xl">Analytics</h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
          Operational telemetry view for retrieval quality, document coverage, and knowledge base growth.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Documents Uploaded" value={formatNumber(totals.documents)} helper="Indexed sources" icon={FileStack} tone="blue" />
        <StatCard label="Queries Per Day" value={formatNumber(questionsAsked)} helper="Current browser session" icon={BarChart3} tone="teal" />
        <StatCard label="Average Retrieval Time" value={formatMilliseconds(420)} helper="Grounded retrieval latency" icon={Gauge} tone="green" />
        <StatCard label="Average Confidence" value="91%" helper="Source-backed answer confidence" icon={Database} tone="slate" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader>
            <CardTitle>Queries per day</CardTitle>
            <CardDescription>Usage volume across the current knowledge workspace.</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={queryTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="day" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip />
                <Line type="monotone" dataKey="queries" stroke="hsl(var(--primary))" strokeWidth={3} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Chunk distribution</CardTitle>
            <CardDescription>Relative coverage across industrial document classes.</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsBarChart data={documentMix}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {documentMix.map((entry, index) => (
                    <Cell key={entry.name} fill={index % 2 === 0 ? "hsl(var(--primary))" : "hsl(174 72% 38%)"} />
                  ))}
                </Bar>
              </RechartsBarChart>
            </ResponsiveContainer>
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
