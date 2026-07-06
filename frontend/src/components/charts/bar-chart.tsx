import { cn } from "@/lib/utils";

interface BarChartProps {
  data: Array<{ label: string; value: number }>;
  className?: string;
}

export function BarChart({ data, className }: BarChartProps) {
  const max = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className={cn("space-y-4", className)}>
      {data.map((item) => (
        <div key={item.label} className="grid grid-cols-[92px_1fr_44px] items-center gap-3">
          <span className="text-xs text-muted-foreground">{item.label}</span>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${(item.value / max) * 100}%` }}
            />
          </div>
          <span className="text-right text-xs font-medium">{item.value}</span>
        </div>
      ))}
    </div>
  );
}
