import { 
  ServerCog, 
  Box,
  BrainCircuit,
  Database,
  Network,
  Info,
  RefreshCw,
  Power,
  UploadCloud,
  CheckCircle2,
  XCircle,
  AlertCircle
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatNumber } from "@/lib/utils";
import type { KnowledgeDocument } from "@/types";
import { useSettings } from "@/context/settings-context";

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
  const settings = useSettings();

  const { data: healthData, refetch, isFetching, isError } = useQuery({
    queryKey: ["backendHealth"],
    queryFn: async () => {
      const res = await fetch("http://127.0.0.1:8000/health");
      if (!res.ok) throw new Error("Backend offline");
      return res.json();
    },
    refetchInterval: 10000,
  });

  const getStatus = (serviceStatus: string | undefined) => {
    if (isError) return "Offline";
    if (serviceStatus === "healthy") return "Healthy";
    if (serviceStatus === "degraded") return "Degraded";
    return "Unknown";
  };

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
          <Button variant="outline" size="sm" className="gap-2 text-xs h-9 bg-background" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh Status
          </Button>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        {/* SECTION 1: Workspace */}
        <Card className="flex flex-col border-border/50 shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-2 text-primary">
              <Box className="h-5 w-5" />
              <CardTitle className="text-lg">Workspace</CardTitle>
            </div>
            <CardDescription>Global preferences and active environment stats.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <SettingInput 
              label="Workspace Name" 
              value={settings.workspaceName} 
              onChange={(v) => settings.updateSetting("workspaceName", v)} 
            />
            <SettingDropdown 
              label="Theme" 
              value={settings.theme} 
              options={[{label: "Light", value: "light"}, {label: "Dark", value: "dark"}, {label: "System Default", value: "system"}]} 
              onChange={(v) => settings.updateSetting("theme", v as any)} 
            />
            <SettingDropdown 
              label="Language" 
              value={settings.language} 
              options={[{label: "English (US)", value: "English (US)"}, {label: "Spanish", value: "Spanish"}, {label: "French", value: "French"}]} 
              onChange={(v) => settings.updateSetting("language", v)} 
            />
            <SettingDropdown 
              label="Timezone" 
              value={settings.timezone} 
              options={[{label: "UTC", value: "UTC"}, {label: "America/New_York", value: "America/New_York"}, {label: "Asia/Kolkata", value: "Asia/Kolkata"}]} 
              onChange={(v) => settings.updateSetting("timezone", v)} 
            />
            <ToggleRow 
              label="Notifications" 
              checked={settings.notificationsEnabled} 
              onChange={(v) => settings.updateSetting("notificationsEnabled", v)} 
            />
            <ToggleRow 
              label="Auto Save" 
              checked={settings.autoSave} 
              onChange={(v) => settings.updateSetting("autoSave", v)} 
            />
          </CardContent>
        </Card>

        {/* SECTION 2: AI Configuration */}
        <Card className="flex flex-col border-border/50 shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-2 text-amber-500">
              <BrainCircuit className="h-5 w-5" />
              <CardTitle className="text-lg">AI Preferences</CardTitle>
            </div>
            <CardDescription>Generative and retrieval model parameters.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <SettingDropdown 
              label="Preferred Model" 
              value={settings.aiModel} 
              options={[
                {label: "Gemini 2.5 Flash", value: "Gemini 2.5 Flash"}, 
                {label: "Gemini 2.5 Pro", value: "Gemini 2.5 Pro"},
                {label: "Gemini 3.1 Pro (High)", value: "Gemini 3.1 Pro (High)"},
              ]} 
              onChange={(v) => settings.updateSetting("aiModel", v)} 
            />
            <SettingSlider 
              label="Temperature" 
              value={settings.temperature} 
              min={0} max={1} step={0.1}
              onChange={(v) => settings.updateSetting("temperature", v)} 
            />
            <SettingSlider 
              label="Max Sources" 
              value={settings.maxSources} 
              min={1} max={20} step={1}
              onChange={(v) => settings.updateSetting("maxSources", v)} 
            />
            <SettingSlider 
              label="Default Top-K" 
              value={settings.topK} 
              min={1} max={50} step={1}
              onChange={(v) => settings.updateSetting("topK", v)} 
            />
            <SettingDropdown 
              label="Answer Length" 
              value={settings.answerLength} 
              options={[{label: "Concise", value: "concise"}, {label: "Detailed", value: "detailed"}, {label: "Comprehensive", value: "comprehensive"}]} 
              onChange={(v) => settings.updateSetting("answerLength", v as any)} 
            />
            <SettingDropdown 
              label="Citation Style" 
              value={settings.citationStyle} 
              options={[{label: "Inline [1]", value: "inline"}, {label: "Footnotes", value: "footnotes"}, {label: "None", value: "none"}]} 
              onChange={(v) => settings.updateSetting("citationStyle", v as any)} 
            />
            <ToggleRow 
              label="Ground Responses" 
              checked={settings.groundResponses} 
              onChange={(v) => settings.updateSetting("groundResponses", v)} 
            />
            <ToggleRow 
              label="Show Confidence Score" 
              checked={settings.showConfidenceScore} 
              onChange={(v) => settings.updateSetting("showConfidenceScore", v)} 
            />
            <ToggleRow 
              label="Auto Expand Sources" 
              checked={settings.autoExpandSources} 
              onChange={(v) => settings.updateSetting("autoExpandSources", v)} 
            />
            <ToggleRow 
              label="Context Visualization" 
              checked={settings.enableContextVisualization} 
              onChange={(v) => settings.updateSetting("enableContextVisualization", v)} 
            />
          </CardContent>
        </Card>

        {/* SECTION 3: Retrieval Settings */}
        <Card className="flex flex-col border-border/50 shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-2 text-blue-500">
              <Database className="h-5 w-5" />
              <CardTitle className="text-lg">Retrieval Settings</CardTitle>
            </div>
            <CardDescription>Configure knowledge extraction methodology.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <SettingDropdown 
              label="Search Type" 
              value={settings.searchType} 
              options={[{label: "Hybrid Search", value: "hybrid"}, {label: "Semantic Only", value: "semantic"}, {label: "Keyword Only", value: "keyword"}]} 
              onChange={(v) => settings.updateSetting("searchType", v as any)} 
            />
            <SettingDropdown 
              label="Search Scope" 
              value={settings.searchScope} 
              options={[{label: "Entire Knowledge Base", value: "entire"}, {label: "Selected Documents Only", value: "selected"}]} 
              onChange={(v) => settings.updateSetting("searchScope", v as any)} 
            />
            <SettingSlider 
              label="Confidence Threshold" 
              value={settings.confidenceThreshold} 
              min={0} max={1} step={0.05}
              onChange={(v) => settings.updateSetting("confidenceThreshold", v)} 
            />
            <ToggleRow 
              label="Auto Metadata Filtering" 
              checked={settings.autoMetadataFiltering} 
              onChange={(v) => settings.updateSetting("autoMetadataFiltering", v)} 
            />
          </CardContent>
        </Card>

        {/* SECTION 4: Document Processing */}
        <Card className="flex flex-col border-border/50 shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-2 text-indigo-500">
              <UploadCloud className="h-5 w-5" />
              <CardTitle className="text-lg">Document Processing</CardTitle>
            </div>
            <CardDescription>Pipelines for ingestion and extraction.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <ToggleRow 
              label="Auto Index Uploads" 
              checked={settings.autoIndexUploads} 
              onChange={(v) => settings.updateSetting("autoIndexUploads", v)} 
            />
            <ToggleRow 
              label="Generate Knowledge Graph" 
              checked={settings.generateKnowledgeGraph} 
              onChange={(v) => settings.updateSetting("generateKnowledgeGraph", v)} 
            />
            <ToggleRow 
              label="Extract Entities" 
              checked={settings.extractEntities} 
              onChange={(v) => settings.updateSetting("extractEntities", v)} 
            />
            <ToggleRow 
              label="Optical Character Recognition (OCR)" 
              checked={settings.ocrEnabled} 
              onChange={(v) => settings.updateSetting("ocrEnabled", v)} 
            />
            <ToggleRow 
              label="Duplicate Detection" 
              checked={settings.duplicateDetection} 
              onChange={(v) => settings.updateSetting("duplicateDetection", v)} 
            />
            <ToggleRow 
              label="Document Versioning" 
              checked={settings.versioning} 
              onChange={(v) => settings.updateSetting("versioning", v)} 
            />
            <ToggleRow 
              label="Generate Auto Summaries" 
              checked={settings.autoSummaries} 
              onChange={(v) => settings.updateSetting("autoSummaries", v)} 
            />
          </CardContent>
        </Card>

        {/* SECTION 5: Backend */}
        <Card className="flex flex-col border-border/50 shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-2 text-emerald-500">
              <ServerCog className="h-5 w-5" />
              <CardTitle className="text-lg">Backend Infrastructure</CardTitle>
            </div>
            <CardDescription>API endpoints and real-time integration metrics.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <SettingRow label="API Endpoint" value="http://127.0.0.1:8000" />
            <SettingRow label="Overall Status" value={isError ? "Offline" : "Online"} status={isError ? "error" : "healthy"} />
            <SettingRow label="Total Vectors" value={healthData ? formatNumber(healthData.vectors) : "..."} />
            <SettingRow label="Total Documents" value={`${formatNumber(totals.documents)} files`} />
            <SettingRow label="Backend Version" value="v1.0.0-rc2" />
          </CardContent>
          <CardFooter className="pt-4 border-t border-border mt-auto">
            <Button variant="secondary" size="sm" className="w-full gap-2 text-xs" onClick={() => refetch()} disabled={isFetching}>
              <Power className="h-3.5 w-3.5" />
              {isError ? "Reconnect Backend" : "Restart Connection"}
            </Button>
          </CardFooter>
        </Card>

        {/* SECTION 6: Application Information */}
        <Card className="flex flex-col border-border/50 shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-2 text-purple-500">
              <Info className="h-5 w-5" />
              <CardTitle className="text-lg">Application Information</CardTitle>
            </div>
            <CardDescription>Software identity and developer details.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 sm:grid-cols-2">
              <InfoBlock label="Project Name" value="INDUS MIND" />
              <InfoBlock label="Version" value="Enterprise v1.2.0" />
              <InfoBlock label="Developer" value="Kapil Meena" />
              <InfoBlock label="Hackathon" value="ET AI Hackathon 2026" />
              <InfoBlock label="License" value="Proprietary / Enterprise" />
              <InfoBlock label="Framework" value="React + FastAPI" />
            </div>
          </CardContent>
        </Card>

        {/* SECTION 7: System Status */}
        <Card className="flex flex-col xl:col-span-2 border-border/50 shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-2 text-rose-500">
              <Network className="h-5 w-5" />
              <CardTitle className="text-lg">Live System Status</CardTitle>
            </div>
            <CardDescription>Real-time connectivity monitors polling every 10 seconds.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-5">
              <StatusBadge label="Backend API" status={isError ? "Offline" : "Healthy"} />
              <StatusBadge label="Gemini LLM" status={getStatus(healthData?.gemini)} />
              <StatusBadge label="Embeddings" status={getStatus(healthData?.embeddings)} />
              <StatusBadge label="ChromaDB" status={getStatus(healthData?.chroma)} />
              {/* Fallback to Ready as health endpoint doesn't return knowledge graph status */}
              <StatusBadge label="Knowledge Graph" status={isError ? "Offline" : "Ready"} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Reusable Components

function ToggleRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between py-2 group">
      <span className="text-sm text-foreground/90 font-medium">{label}</span>
      <button 
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${checked ? 'bg-primary' : 'bg-input'}`}
      >
        <span 
          aria-hidden="true"
          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-background shadow-lg ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-2' : '-translate-x-2'}`}
        />
      </button>
    </div>
  );
}

function SettingDropdown({ label, value, options, onChange }: { label: string; value: string; options: {label: string; value: string}[]; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between py-2 gap-2">
      <span className="text-sm text-foreground/90 font-medium shrink-0">{label}</span>
      <select 
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full sm:w-[180px] rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring cursor-pointer"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );
}

function SettingSlider({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void }) {
  return (
    <div className="flex flex-col py-2 gap-2">
      <div className="flex justify-between items-center">
        <span className="text-sm text-foreground/90 font-medium">{label}</span>
        <span className="text-xs font-mono bg-muted px-2 py-1 rounded-md">{value}</span>
      </div>
      <input 
        type="range" 
        min={min} 
        max={max} 
        step={step} 
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 bg-input rounded-lg appearance-none cursor-pointer accent-primary"
      />
    </div>
  );
}

function SettingInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between py-2 gap-2">
      <span className="text-sm text-foreground/90 font-medium shrink-0">{label}</span>
      <Input 
        value={value} 
        onChange={(e) => onChange(e.target.value)} 
        className="h-9 w-full sm:w-[220px]"
      />
    </div>
  );
}

function SettingRow({ label, value, status }: { label: string; value: string; status?: "healthy" | "warning" | "error" }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-border/40 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        {status === "healthy" && <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />}
        {status === "warning" && <span className="h-2 w-2 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]" />}
        {status === "error" && <span className="h-2 w-2 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]" />}
        <span className="text-sm font-medium">{value}</span>
      </div>
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col space-y-1 p-3 rounded-lg bg-muted/40 border border-border/50">
      <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}

function StatusBadge({ label, status }: { label: string; status: string }) {
  const isHealthy = status === "Healthy" || status === "Ready";
  const isDegraded = status === "Degraded";
  const isOffline = status === "Offline" || status === "Unknown";

  return (
    <div className={`flex flex-col gap-2 rounded-xl border px-4 py-3 shadow-sm transition-all
      ${isHealthy ? "border-emerald-500/20 bg-emerald-500/5" : ""}
      ${isDegraded ? "border-amber-500/20 bg-amber-500/5" : ""}
      ${isOffline ? "border-rose-500/20 bg-rose-500/5" : ""}
    `}>
      <span className="text-xs font-medium text-muted-foreground truncate">{label}</span>
      <div className="flex items-center gap-1.5">
        {isHealthy && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
        {isDegraded && <AlertCircle className="h-4 w-4 text-amber-500" />}
        {isOffline && <XCircle className="h-4 w-4 text-rose-500" />}
        
        <span className={`text-sm font-semibold 
          ${isHealthy ? "text-emerald-500" : ""}
          ${isDegraded ? "text-amber-500" : ""}
          ${isOffline ? "text-rose-500" : ""}
        `}>
          {status}
        </span>
      </div>
    </div>
  );
}
