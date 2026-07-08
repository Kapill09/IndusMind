import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Cog,
  Cpu,
  File,
  FileText,
  Scale,
  Shield,
  Wrench,
} from "lucide-react";
import type { NodeColorConfig } from "@/types/knowledge-graph";

/** Maps each backend node type to its visual style. */
export const NODE_COLORS: Record<string, NodeColorConfig> = {
  Document: {
    bg: "bg-slate-100",
    bgDark: "dark:bg-slate-800",
    border: "border-slate-300",
    borderDark: "dark:border-slate-600",
    text: "text-slate-700",
    textDark: "dark:text-slate-200",
    glow: "rgba(100,116,139,0.35)",
  },
  Equipment: {
    bg: "bg-blue-100",
    bgDark: "dark:bg-blue-900/50",
    border: "border-blue-300",
    borderDark: "dark:border-blue-700",
    text: "text-blue-700",
    textDark: "dark:text-blue-200",
    glow: "rgba(59,130,246,0.35)",
  },
  "Problem Statements": {
    bg: "bg-purple-100",
    bgDark: "dark:bg-purple-900/50",
    border: "border-purple-300",
    borderDark: "dark:border-purple-700",
    text: "text-purple-700",
    textDark: "dark:text-purple-200",
    glow: "rgba(147,51,234,0.35)",
  },
  Technologies: {
    bg: "bg-cyan-100",
    bgDark: "dark:bg-cyan-900/50",
    border: "border-cyan-300",
    borderDark: "dark:border-cyan-700",
    text: "text-cyan-700",
    textDark: "dark:text-cyan-200",
    glow: "rgba(6,182,212,0.35)",
  },
  "Maintenance concepts": {
    bg: "bg-orange-100",
    bgDark: "dark:bg-orange-900/50",
    border: "border-orange-300",
    borderDark: "dark:border-orange-700",
    text: "text-orange-700",
    textDark: "dark:text-orange-200",
    glow: "rgba(249,115,22,0.35)",
  },
  "Safety terms": {
    bg: "bg-red-100",
    bgDark: "dark:bg-red-900/50",
    border: "border-red-300",
    borderDark: "dark:border-red-700",
    text: "text-red-700",
    textDark: "dark:text-red-200",
    glow: "rgba(239,68,68,0.35)",
  },
  Standards: {
    bg: "bg-green-100",
    bgDark: "dark:bg-green-900/50",
    border: "border-green-300",
    borderDark: "dark:border-green-700",
    text: "text-green-700",
    textDark: "dark:text-green-200",
    glow: "rgba(34,197,94,0.35)",
  },
  Regulations: {
    bg: "bg-emerald-100",
    bgDark: "dark:bg-emerald-900/50",
    border: "border-emerald-300",
    borderDark: "dark:border-emerald-700",
    text: "text-emerald-700",
    textDark: "dark:text-emerald-200",
    glow: "rgba(16,185,129,0.35)",
  },
  SOPs: {
    bg: "bg-indigo-100",
    bgDark: "dark:bg-indigo-900/50",
    border: "border-indigo-300",
    borderDark: "dark:border-indigo-700",
    text: "text-indigo-700",
    textDark: "dark:text-indigo-200",
    glow: "rgba(99,102,241,0.35)",
  },
  Page: {
    bg: "bg-yellow-100",
    bgDark: "dark:bg-yellow-900/50",
    border: "border-yellow-300",
    borderDark: "dark:border-yellow-700",
    text: "text-yellow-700",
    textDark: "dark:text-yellow-200",
    glow: "rgba(234,179,8,0.35)",
  },
  Chunk: {
    bg: "bg-zinc-100",
    bgDark: "dark:bg-zinc-800",
    border: "border-zinc-300",
    borderDark: "dark:border-zinc-600",
    text: "text-zinc-700",
    textDark: "dark:text-zinc-200",
    glow: "rgba(113,113,122,0.35)",
  },
};

/** Fallback color when the node type is not recognised. */
export const DEFAULT_NODE_COLOR: NodeColorConfig = {
  bg: "bg-gray-100",
  bgDark: "dark:bg-gray-800",
  border: "border-gray-300",
  borderDark: "dark:border-gray-600",
  text: "text-gray-700",
  textDark: "dark:text-gray-200",
  glow: "rgba(156,163,175,0.35)",
};

/** Maps each node type to a lucide icon component. */
export const NODE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Document: FileText,
  Equipment: Cog,
  "Problem Statements": AlertTriangle,
  Technologies: Cpu,
  "Maintenance concepts": Wrench,
  "Safety terms": Shield,
  Standards: CheckCircle2,
  Regulations: Scale,
  SOPs: BookOpen,
  Page: File,
  Chunk: File,
};

/** Hex colour used for the React Flow minimap node colour. */
export const MINIMAP_COLORS: Record<string, string> = {
  Document: "#64748b",
  Equipment: "#3b82f6",
  "Problem Statements": "#a855f7",
  Technologies: "#06b6d4",
  "Maintenance concepts": "#f97316",
  "Safety terms": "#ef4444",
  Standards: "#22c55e",
  Regulations: "#10b981",
  SOPs: "#6366f1",
  Page: "#eab308",
  Chunk: "#71717a",
};

/** Default dimensions for custom graph nodes. */
export const NODE_WIDTH = 180;
export const NODE_HEIGHT = 52;
