import { 
  ServerCog, 
  ShieldCheck, 
  SlidersHorizontal,
  Box,
  BrainCircuit,
  Database,
  Network,
  Info,
  RefreshCw,
  Power,
  RotateCcw,
  UploadCloud,
  CheckCircle2
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { formatNumber } from "@/lib/utils";
import type { KnowledgeDocument } from "@/types";

interface SettingsPageProps {
  documents?: KnowledgeDocument[];
  totals?: {
    documents: number;
    pages: number;
    chunks: number;
    vectors: number;
  };
}

export function SettingsPage({ documents = [], totals = { documents: 0, pages: 0, chunks: 0, vectors: 0 } }: SettingsPageProps) {
  // Use local storage to check theme if we want, or just assume from app shell
  const isDarkMode = document.documentElement.classList.contains("dark");

  return (
    <div className="space-y-8 pb-8">
      <section className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Badge variant="outline" className="mb-3 bg-muted/50 border-border">Configuration Center</Badge>
          <h1 className="text-2xl font-semibold tracking-[-0.02em] md:text-3xl">Enterprise Settings</h1>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
            Manage system architecture, view infrastructure status, and configure AI behavior.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" className="gap-2 text-xs h-9 bg-background">
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh Status
          </Button>
          <Button variant="outline" size="sm" className="gap-2 text-xs h-9 bg-background">
            <UploadCloud className="h-3.5 w-3.5" />
            Sync Documents
          </Button>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        {/* SECTION 1: Workspace */}
        <Card className="flex flex-col">
          <CardHeader>
            <div className="flex items-center gap-2 text-primary">
              <Box className="h-5 w-5" />
              <CardTitle className="text-lg">Workspace</CardTitle>
            </div>
            <CardDescription>Global preferences and active environment stats.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <SettingRow label="Workspace Name" value="ET AI Hackathon" />
            <SettingRow label="Current Theme" value={isDarkMode ? "Dark" : "Light"} />
            <SettingRow label="Language" value="English (US)" />
            <SettingRow label="Dark Mode" value={isDarkMode ? "Enabled" : "Disabled"} />
            <SettingRow label="Knowledge Base Size" value={`${formatNumber(totals.vectors)} vectors`} />
            <SettingRow label="Uploaded Documents" value={`${formatNumber(totals.documents)} files`} />
          </CardContent>
        </Card>

        {/* SECTION 2: AI Configuration */}
        <Card className="flex flex-col">
          <CardHeader>
            <div className="flex items-center gap-2 text-amber-500">
              <BrainCircuit className="h-5 w-5" />
              <CardTitle className="text-lg">AI Configuration</CardTitle>
            </div>
            <CardDescription>Generative and retrieval model parameters.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <SettingRow label="Current Model" value="Gemini 2.5 Flash" />
            <SettingRow label="Embedding Model" value="all-MiniLM-L6-v2" />
            <SettingRow label="Maximum Sources" value="5" />
            <SettingRow label="Max Retrieved Chunks" value="10" />
            <SettingRow label="Grounding Enabled" value="Yes" badge />
            <SettingRow label="Semantic Search" value="Enabled" badge />
            <SettingRow label="Hybrid Search" value="Enabled" badge />
          </CardContent>
        </Card>

        {/* SECTION 3: Knowledge Base */}
        <Card className="flex flex-col">
          <CardHeader>
            <div className="flex items-center gap-2 text-blue-500">
              <Database className="h-5 w-5" />
              <CardTitle className="text-lg">Knowledge Base</CardTitle>
            </div>
            <CardDescription>Database engines and vector storage configuration.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <SettingRow label="Vector Database" value="ChromaDB" />
            <SettingRow label="Knowledge Graph" value="Enabled" badge />
            <SettingRow label="Entity Extraction" value="Enabled" badge />
            <SettingRow label="Embedding Dimension" value="384" />
            <SettingRow label="Chunk Size" value="1000 tokens" />
            <SettingRow label="Current Configuration" value="Production" />
          </CardContent>
          <CardFooter className="pt-4 border-t border-border mt-auto">
            <Button variant="secondary" size="sm" className="w-full gap-2 text-xs">
              <RotateCcw className="h-3.5 w-3.5" />
              Rebuild Knowledge Graph
            </Button>
          </CardFooter>
        </Card>

        {/* SECTION 4: Backend */}
        <Card className="flex flex-col">
          <CardHeader>
            <div className="flex items-center gap-2 text-emerald-500">
              <ServerCog className="h-5 w-5" />
              <CardTitle className="text-lg">Backend Infrastructure</CardTitle>
            </div>
            <CardDescription>API endpoints and integration metrics.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <SettingRow label="API Endpoint" value="http://127.0.0.1:8000" />
            <SettingRow label="Backend Status" value="Online" status="healthy" />
            <SettingRow label="Collection Name" value="indus_mind_docs" />
            <SettingRow label="Health Status" value="Healthy" status="healthy" />
            <SettingRow label="Latency" value="< 50ms" />
            <SettingRow label="Backend Version" value="v1.0.0-rc2" />
          </CardContent>
          <CardFooter className="pt-4 border-t border-border mt-auto">
            <Button variant="secondary" size="sm" className="w-full gap-2 text-xs">
              <Power className="h-3.5 w-3.5" />
              Reconnect Backend
            </Button>
          </CardFooter>
        </Card>

        {/* SECTION 5: Application Information */}
        <Card className="flex flex-col xl:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2 text-purple-500">
              <Info className="h-5 w-5" />
              <CardTitle className="text-lg">Application Information</CardTitle>
            </div>
            <CardDescription>Software identity and developer details.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3">
              <InfoBlock label="Project Name" value="INDUS MIND" />
              <InfoBlock label="Version" value="Enterprise v1.2.0" />
              <InfoBlock label="Developer" value="Kapil Meena" />
              <InfoBlock label="Hackathon" value="ET AI Hackathon 2026" />
              <InfoBlock label="License" value="Proprietary / Enterprise" />
              <InfoBlock label="Framework" value="React + FastAPI" />
            </div>
          </CardContent>
        </Card>

        {/* SECTION 6: System Status */}
        <Card className="flex flex-col xl:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2 text-rose-500">
              <Network className="h-5 w-5" />
              <CardTitle className="text-lg">System Status</CardTitle>
            </div>
            <CardDescription>Real-time connectivity and service health monitors.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-5">
              <StatusBadge label="Backend" status="Healthy" />
              <StatusBadge label="LLM" status="Connected" />
              <StatusBadge label="Embeddings" status="Ready" />
              <StatusBadge label="Knowledge Graph" status="Ready" />
              <StatusBadge label="Documents" status="Indexed" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Helper components for consistent layout

function SettingRow({ label, value, badge, status }: { label: string; value: string; badge?: boolean; status?: "healthy" | "warning" | "error" }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        {status === "healthy" && <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />}
        {status === "warning" && <span className="h-2 w-2 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]" />}
        {status === "error" && <span className="h-2 w-2 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]" />}
        
        {badge ? (
          <Badge variant="secondary" className="font-normal text-xs bg-muted/60">{value}</Badge>
        ) : (
          <span className="text-sm font-medium">{value}</span>
        )}
      </div>
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col space-y-1">
      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}

function StatusBadge({ label, status }: { label: string; status: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3 shadow-sm">
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
      <div className="flex items-center gap-1.5">
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        <span className="text-xs font-semibold text-emerald-500">{status}</span>
      </div>
    </div>
  );
}
