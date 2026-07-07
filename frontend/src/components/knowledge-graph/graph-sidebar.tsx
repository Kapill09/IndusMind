import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Cog,
  Cpu,
  FileText,
  RotateCcw,
  Scale,
  Search,
  Shield,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { KGFilterKey, KGStats } from "@/types/knowledge-graph";

interface GraphSidebarProps {
  stats: KGStats;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  activeFilters: Set<KGFilterKey>;
  onToggleFilter: (key: KGFilterKey) => void;
  onResetFilters: () => void;
}

const STAT_ITEMS: {
  key: keyof KGStats;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}[] = [
  { key: "documents", label: "Documents", icon: FileText, color: "text-slate-500" },
  { key: "problemStatements", label: "Problem Statements", icon: AlertTriangle, color: "text-purple-500" },
  { key: "equipment", label: "Equipment", icon: Cog, color: "text-blue-500" },
  { key: "technologies", label: "Technologies", icon: Cpu, color: "text-cyan-500" },
  { key: "maintenance", label: "Maintenance Records", icon: Wrench, color: "text-orange-500" },
  { key: "safety", label: "Safety Entities", icon: Shield, color: "text-red-500" },
  { key: "standards", label: "Standards", icon: CheckCircle2, color: "text-green-500" },
  { key: "regulations", label: "Regulations", icon: Scale, color: "text-emerald-500" },
];

const FILTER_CHIPS: {
  key: KGFilterKey;
  label: string;
  dot: string;
}[] = [
  { key: "Document", label: "Document", dot: "bg-slate-400" },
  { key: "Equipment", label: "Equipment", dot: "bg-blue-500" },
  { key: "Technology", label: "Technology", dot: "bg-cyan-500" },
  { key: "Safety", label: "Safety", dot: "bg-red-500" },
  { key: "Maintenance", label: "Maintenance", dot: "bg-orange-500" },
  { key: "Problem Statement", label: "Problem Statement", dot: "bg-purple-500" },
  { key: "Standards", label: "Standards", dot: "bg-green-500" },
  { key: "Regulations", label: "Regulations", dot: "bg-emerald-500" },
];

export function GraphSidebar({
  stats,
  searchQuery,
  onSearchChange,
  activeFilters,
  onToggleFilter,
  onResetFilters,
}: GraphSidebarProps) {
  const hasActiveFilters = activeFilters.size > 0 || searchQuery.trim().length > 0;

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-border bg-card/50 lg:w-80">
      {/* ── Stats ───────────────────────────────────────────────── */}
      <div className="border-b border-border p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Knowledge Statistics
        </h3>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {STAT_ITEMS.map((item) => {
            const Icon = item.icon;
            const value = stats[item.key] as number;
            return (
              <div
                key={item.key}
                className="flex items-center gap-2 rounded-lg border border-border bg-background/60 px-2.5 py-2"
              >
                <Icon className={cn("h-3.5 w-3.5 shrink-0", item.color)} />
                <div className="min-w-0">
                  <p className="text-sm font-semibold leading-tight">{value}</p>
                  <p className="truncate text-[10px] leading-tight text-muted-foreground">
                    {item.label}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Search ──────────────────────────────────────────────── */}
      <div className="border-b border-border p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Search
        </h3>
        <div className="mt-2 flex items-center gap-2 rounded-lg border border-input bg-background px-2.5 py-1.5">
          <Search className="h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search entities..."
            className="h-7 border-0 bg-transparent px-0 text-sm shadow-none focus-visible:ring-0"
            aria-label="Search knowledge graph entities"
          />
        </div>
      </div>

      {/* ── Filters ─────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Filters
        </h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {FILTER_CHIPS.map((chip) => {
            const isActive = activeFilters.has(chip.key);
            return (
              <button
                key={chip.key}
                onClick={() => onToggleFilter(chip.key)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all duration-150",
                  isActive
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <span className={cn("h-2 w-2 rounded-full", chip.dot)} />
                {chip.label}
              </button>
            );
          })}
        </div>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-3 w-full gap-1.5 text-xs text-muted-foreground"
            onClick={onResetFilters}
          >
            <RotateCcw className="h-3 w-3" />
            Reset Filters
          </Button>
        )}
      </div>

      {/* ── Footer ──────────────────────────────────────────────── */}
      <div className="border-t border-border p-4">
        <div className="flex items-baseline justify-between text-xs text-muted-foreground">
          <span>{stats.totalNodes} nodes</span>
          <span>{stats.totalEdges} edges</span>
        </div>
      </div>
    </aside>
  );
}
