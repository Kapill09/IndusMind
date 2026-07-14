import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { 
  Activity,
  BarChart3, 
  Cpu, 
  Database, 
  FileStack, 
  Gauge, 
  Network,
  Share2,
  Timer,
  Zap,
} from "lucide-react";
import { 
  ResponsiveContainer, 
  BarChart as RechartsBarChart, 
  PieChart, 
  Pie,
  CartesianGrid, 
  Cell, 
  Tooltip, 
  XAxis, 
  YAxis, 
  Bar 
} from "recharts";
import { StatCard } from "@/components/dashboard/stat-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatMilliseconds, formatNumber } from "@/lib/utils";
import type { ChatMessage, KnowledgeDocument } from "@/types";
import { fetchKnowledgeGraph } from "@/lib/api";

const CHART_COLORS = [
  "hsl(var(--primary))",
  "hsl(174 72% 38%)", // teal
  "hsl(270 60% 50%)", // purple
  "hsl(32 90% 55%)",  // orange
  "hsl(210 90% 60%)", // blue
  "hsl(340 70% 55%)", // pink
];

interface AnalyticsPageProps {
  totals: {
    documents: number;
    pages: number;
    chunks: number;
    vectors: number;
  };
  documents: KnowledgeDocument[];
  messages: ChatMessage[];
}

export function AnalyticsPage({ totals, documents, messages }: AnalyticsPageProps) {
  // Fetch global Knowledge Graph stats
  const kgQuery = useQuery({
    queryKey: ["analytics", "knowledge-graph"],
    queryFn: fetchKnowledgeGraph,
    staleTime: 5 * 60_000,
  });

  const kgNodes = kgQuery.data?.nodes ?? [];
  const kgEdges = kgQuery.data?.edges ?? [];

  // ── Derived Metrics ──
  
  const stats = useMemo(() => {
    const assistantMsgs = messages.filter((m) => m.role === "assistant");
    const count = assistantMsgs.length || 1; // avoid div by zero

    let totalRetrievalMs = 0;
    let totalConfidence = 0;
    let totalSources = 0;
    let totalGenMs = 0;

    const documentRetrievalCounts: Record<string, number> = {};

    assistantMsgs.forEach((msg) => {
      // Retrieval time from backend
      const retTime = msg.latencyMs ?? 0;
      totalRetrievalMs += retTime;

      // Confidence
      totalConfidence += msg.confidence ?? 0;

      // Sources
      const sources = msg.sources ?? [];
      totalSources += sources.length;

      // Estimate Generation Time (assume ~40 tokens/sec, 1 token ≈ 4 chars)
      const tokenEstimate = (msg.content?.length ?? 0) / 4;
      const genTimeMs = (tokenEstimate / 40) * 1000;
      totalGenMs += genTimeMs;

      // Track most retrieved documents
      sources.forEach((source) => {
        const docName = source.metadata?.filename || source.metadata?.document_id || "Unknown Source";
        documentRetrievalCounts[docName] = (documentRetrievalCounts[docName] || 0) + 1;
      });
    });

    // Top 5 Retrieved Documents
    const topDocuments = Object.entries(documentRetrievalCounts)
      .map(([name, count]) => ({ name: name.replace(".pdf", ""), frequency: count }))
      .sort((a, b) => b.frequency - a.frequency)
      .slice(0, 5);

    // AI Query History (Latest 5)
    const recentQueries = assistantMsgs
      .slice(-5)
      .reverse()
      .map((msg) => ({
        id: msg.id,
        question: msg.question || "Contextual Follow-up",
        confidence: msg.confidence ?? 0,
        sources: msg.sources?.length ?? 0,
        latency: msg.latencyMs ?? 0,
      }));

    return {
      avgRetrieval: totalRetrievalMs / count,
      avgGen: totalGenMs / count,
      avgTotal: (totalRetrievalMs + totalGenMs) / count,
      avgConfidence: totalConfidence / count,
      avgSources: totalSources / count,
      topDocuments,
      recentQueries,
    };
  }, [messages]);

  // Source Distribution Data
  const sourceDistribution = useMemo(() => {
    return documents
      .filter((doc) => doc.chunks > 0)
      .map((doc) => ({
        name: doc.filename.replace(".pdf", ""),
        value: doc.chunks,
      }))
      .sort((a, b) => b.value - a.value);
  }, [documents]);

  // KG Stats
  const kgMetrics = useMemo(() => {
    const entityTypes = new Set(kgNodes.map((n) => n.type));
    const docsConnected = kgNodes.filter((n) => n.type === "Document").length;
    
    return {
      nodes: kgNodes.length,
      edges: kgEdges.length,
      types: entityTypes.size,
      docsConnected,
      avgRels: kgNodes.length ? (kgEdges.length / kgNodes.length).toFixed(1) : "0.0",
    };
  }, [kgNodes, kgEdges]);

  return (
    <div className="space-y-8 pb-8">
      <section>
        <h1 className="text-2xl font-semibold tracking-[-0.02em] md:text-3xl">Analytics Dashboard</h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
          Enterprise operational telemetry for retrieval quality, infrastructure health, and generative performance.
        </p>
      </section>

      {/* ── TOP SUMMARY CARDS ── */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard 
          label="Documents Indexed" 
          value={formatNumber(totals.documents)} 
          helper={`${formatNumber(totals.chunks)} total chunks generated`} 
          icon={FileStack} 
          tone="blue" 
        />
        <StatCard 
          label="Knowledge Graph Size" 
          value={formatNumber(kgMetrics.nodes)} 
          helper={`${formatNumber(kgMetrics.edges)} semantic relationships`} 
          icon={Share2} 
          tone="purple" 
        />
        <StatCard 
          label="Average Retrieval Time" 
          value={stats.avgRetrieval > 0 ? formatMilliseconds(stats.avgRetrieval) : "-"} 
          helper={`Avg Response: ${stats.avgTotal > 0 ? formatMilliseconds(stats.avgTotal) : "-"}`} 
          icon={Zap} 
          tone="green" 
        />
        <StatCard 
          label="Average Grounding" 
          value={stats.avgConfidence > 0 ? `${Math.round(stats.avgConfidence)}%` : "-"} 
          helper={`${stats.avgSources > 0 ? stats.avgSources.toFixed(1) : 0} sources cited per answer`} 
          icon={Database} 
          tone="teal" 
        />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-6">
          {/* ── SECTION 1: RETRIEVAL PERFORMANCE ── */}
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                <CardTitle className="text-base">Retrieval & Generation Performance</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricBox label="Avg Retrieval Latency" value={formatMilliseconds(stats.avgRetrieval)} />
                <MetricBox label="Avg LLM Generation" value={formatMilliseconds(stats.avgGen)} />
                <MetricBox label="Semantic Similarity" value={`${Math.round(stats.avgConfidence)}%`} />
                <MetricBox label="End-to-End Latency" value={formatMilliseconds(stats.avgTotal)} />
              </div>
            </CardContent>
          </Card>

          {/* ── SECTION 3: MOST RETRIEVED DOCUMENTS ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Most Retrieved Documents</CardTitle>
              <CardDescription>Top sources driving AI answers based on historical queries.</CardDescription>
            </CardHeader>
            <CardContent className="h-64">
              {stats.topDocuments.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsBarChart data={stats.topDocuments} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="hsl(var(--border))" />
                    <XAxis type="number" tickLine={false} axisLine={false} hide />
                    <YAxis dataKey="name" type="category" tickLine={false} axisLine={false} width={140} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip cursor={{ fill: "hsl(var(--muted)/0.4)" }} contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: "8px" }} />
                    <Bar dataKey="frequency" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} barSize={24} />
                  </RechartsBarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  No retrieval data available yet.
                </div>
              )}
            </CardContent>
          </Card>

          {/* ── SECTION 5: AI QUERY HISTORY ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent AI Queries</CardTitle>
              <CardDescription>Latest telemetry for grounded AI responses.</CardDescription>
            </CardHeader>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-muted/50 text-muted-foreground text-xs uppercase border-y border-border">
                  <tr>
                    <th className="px-4 py-3 font-medium">Query Context</th>
                    <th className="px-4 py-3 font-medium">Confidence</th>
                    <th className="px-4 py-3 font-medium">Sources</th>
                    <th className="px-4 py-3 font-medium text-right">Retrieval</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {stats.recentQueries.length > 0 ? (
                    stats.recentQueries.map((q) => (
                      <tr key={q.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-3 font-medium truncate max-w-[200px]" title={q.question}>
                          {q.question}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className={q.confidence >= 80 ? "text-green-500 border-green-500/30" : "text-amber-500 border-amber-500/30"}>
                            {q.confidence}%
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{q.sources} cited</td>
                        <td className="px-4 py-3 text-right tabular-nums">{q.latency}ms</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                        No queries executed yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          {/* ── SECTION 6: SYSTEM HEALTH ── */}
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-teal-500" />
                <CardTitle className="text-base">System Architecture</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <HealthRow label="LLM Generator" value="Gemini 2.5 Flash" />
                <HealthRow label="Embedding Model" value="Gemini 1.5 Pro Embeddings" />
                <HealthRow label="Vector Database" value="ChromaDB" />
                <HealthRow label="Graph Backend" value="In-Memory NetworkX" />
                <HealthRow label="API Framework" value="FastAPI (Python 3.11)" />
                <div className="pt-2 border-t border-border mt-2 flex items-center justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <Badge className="bg-emerald-500/15 text-emerald-500 hover:bg-emerald-500/25 border-emerald-500/20">Operational</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ── SECTION 4: SOURCE DISTRIBUTION ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Vector Distribution</CardTitle>
              <CardDescription>Contribution by document to the knowledge base.</CardDescription>
            </CardHeader>
            <CardContent className="h-64">
              {sourceDistribution.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sourceDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                      stroke="none"
                    >
                      {sourceDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value: number) => [`${value} chunks`, "Vector Count"]}
                      contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: "8px" }} 
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  No indexed documents.
                </div>
              )}
              <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1">
                {sourceDistribution.slice(0, 4).map((doc, i) => (
                  <div key={doc.name} className="flex items-center gap-1.5 text-xs text-muted-foreground truncate" title={doc.name}>
                    <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <span className="truncate">{doc.name}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* ── SECTION 7: KNOWLEDGE GRAPH STATS ── */}
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center gap-2">
                <Network className="h-4 w-4 text-purple-500" />
                <CardTitle className="text-base">Global Knowledge Graph</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <MetricBox label="Total Entities" value={formatNumber(kgMetrics.nodes)} compact />
                <MetricBox label="Relationships" value={formatNumber(kgMetrics.edges)} compact />
                <MetricBox label="Unique Types" value={kgMetrics.types} compact />
                <MetricBox label="Docs Connected" value={kgMetrics.docsConnected} compact />
              </div>
              <div className="mt-4 pt-4 border-t border-border text-xs text-center text-muted-foreground">
                Average {kgMetrics.avgRels} connections per entity
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function MetricBox({ label, value, compact = false }: { label: string; value: string | number; compact?: boolean }) {
  return (
    <div className={`rounded-xl border border-border bg-muted/40 ${compact ? 'p-3' : 'p-4'}`}>
      <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1 line-clamp-1" title={label}>{label}</p>
      <p className={`${compact ? 'text-lg' : 'text-2xl'} font-semibold text-foreground`}>{value}</p>
    </div>
  );
}

function HealthRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right text-foreground">{value}</span>
    </div>
  );
}
