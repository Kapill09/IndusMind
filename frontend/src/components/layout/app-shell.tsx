import {
  BarChart3,
  Bot,
  FileText,
  LayoutDashboard,
  Menu,
  Moon,
  Search,
  Settings,
  Share2,
  Sun,
  UploadCloud,
  X,
} from "lucide-react";
import type React from "react";
import { cn } from "@/lib/utils";
import type { PageKey } from "@/types";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const navigation: Array<{ key: PageKey; label: string; icon: React.ComponentType<{ className?: string }> }> = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "assistant", label: "AI Assistant", icon: Bot },
  { key: "documents", label: "Documents", icon: FileText },
  { key: "analytics", label: "Analytics", icon: BarChart3 },
  { key: "knowledge-graph", label: "Knowledge Graph", icon: Share2 },
  { key: "settings", label: "Settings", icon: Settings },
];

interface AppShellProps {
  activePage: PageKey;
  onNavigate: (page: PageKey) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  darkMode: boolean;
  setDarkMode: (value: boolean) => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  children: React.ReactNode;
}

export function AppShell({
  activePage,
  onNavigate,
  sidebarOpen,
  setSidebarOpen,
  darkMode,
  setDarkMode,
  searchQuery,
  onSearchQueryChange,
  children,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-background">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-border bg-card/95 shadow-[0_20px_60px_-24px_rgba(15,23,42,0.28)] backdrop-blur transition-transform lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Primary navigation"
      >
        <div className="flex h-16 items-center justify-between border-b border-border px-5">
          <button
            className="flex items-center gap-3 text-left"
            onClick={() => onNavigate("dashboard")}
            aria-label="Go to dashboard"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-sm font-semibold text-primary-foreground shadow-sm">
              IM
            </div>
            <div>
              <p className="text-sm font-semibold">INDUS MIND</p>
              <p className="text-xs text-muted-foreground">Industrial RAG</p>
            </div>
          </button>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.key;
            return (
              <button
                key={item.key}
                onClick={() => {
                  onNavigate(item.key);
                  setSidebarOpen(false);
                }}
                className={cn(
                  "group relative flex h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium transition-all duration-200",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:-translate-y-0.5 hover:bg-muted hover:text-foreground",
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <span
                  className={cn(
                    "absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-primary transition-all",
                    isActive ? "opacity-100" : "opacity-0",
                  )}
                />
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="border-t border-border p-4">
          <div className="rounded-2xl border border-border bg-muted/60 p-4">
            <p className="text-sm font-semibold">Current workspace</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">ET AI Hackathon · Industrial Knowledge Intelligence</p>
          </div>
        </div>
      </aside>

      {sidebarOpen ? (
        <button
          className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation overlay"
        />
      ) : null}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/75 md:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold md:text-base">INDUS MIND Enterprise Console</p>
            <p className="hidden text-xs text-muted-foreground sm:block">Industrial Knowledge Intelligence for engineering and plant teams</p>
          </div>

          <div className="hidden w-full max-w-sm items-center gap-2 rounded-xl border border-input bg-background px-3 py-2 shadow-sm md:flex">
            <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <Input
              value={searchQuery}
              onChange={(event) => onSearchQueryChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onNavigate("documents");
                }
              }}
              className="h-8 border-0 px-0 shadow-none focus-visible:ring-0"
              placeholder="Search manuals, SOPs, reports..."
              aria-label="Search knowledge base"
            />
          </div>

          <Button onClick={() => onNavigate("upload")} className="shrink-0">
            <UploadCloud className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">Upload</span>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Toggle theme"
            onClick={() => setDarkMode(!darkMode)}
            className="shrink-0"
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
          <Avatar className="shrink-0" />
        </header>

        <main className="px-4 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
