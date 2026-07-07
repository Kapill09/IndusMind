import { useEffect, useRef, useState } from "react";
import { Bot, Copy, Focus, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ContextMenuPosition {
  x: number;
  y: number;
}

interface GraphContextMenuProps {
  position: ContextMenuPosition | null;
  nodeLabel: string;
  onClose: () => void;
  onCenterNode: () => void;
  onHighlightConnected: () => void;
  onAskAI: () => void;
  onCopyId: () => void;
}

export function GraphContextMenu({
  position,
  nodeLabel,
  onClose,
  onCenterNode,
  onHighlightConnected,
  onAskAI,
  onCopyId,
}: GraphContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (position) {
      // Delay for smooth entrance
      requestAnimationFrame(() => setVisible(true));
    } else {
      setVisible(false);
    }
  }, [position]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as globalThis.Node)) {
        onClose();
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [onClose]);

  if (!position) return null;

  const items = [
    { icon: Focus, label: "Center on Node", onClick: onCenterNode },
    { icon: Sparkles, label: "Highlight Connected", onClick: onHighlightConnected },
    { icon: Bot, label: "Ask AI", onClick: onAskAI },
    { icon: Copy, label: "Copy Node ID", onClick: onCopyId },
  ];

  return (
    <div
      ref={menuRef}
      className={cn(
        "fixed z-50 min-w-[180px] rounded-xl border border-border bg-card p-1 shadow-lg backdrop-blur transition-all duration-150",
        visible ? "scale-100 opacity-100" : "scale-95 opacity-0"
      )}
      style={{ left: position.x, top: position.y }}
      role="menu"
    >
      <div className="border-b border-border px-3 py-2">
        <p className="truncate text-xs font-semibold">{nodeLabel}</p>
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.label}
            onClick={() => {
              item.onClick();
              onClose();
            }}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            role="menuitem"
          >
            <Icon className="h-3.5 w-3.5" />
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
