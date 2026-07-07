import { Skeleton } from "@/components/ui/skeleton";

export function GraphLoadingState() {
  return (
    <div className="flex h-full">
      {/* Sidebar skeleton */}
      <div className="flex w-72 shrink-0 flex-col border-r border-border bg-card/50 p-4 lg:w-80">
        <Skeleton className="mb-4 h-4 w-32" />
        <div className="grid grid-cols-2 gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
        <Skeleton className="mt-6 h-4 w-20" />
        <Skeleton className="mt-2 h-9 rounded-lg" />
        <Skeleton className="mt-6 h-4 w-16" />
        <div className="mt-3 flex flex-wrap gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-7 w-20 rounded-lg" />
          ))}
        </div>
      </div>

      {/* Canvas skeleton */}
      <div className="relative flex-1 bg-background p-8">
        {/* Simulated graph nodes */}
        <div className="flex h-full items-center justify-center">
          <div className="relative h-80 w-96">
            {/* Faux edges */}
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 384 320">
              <line
                x1="120"
                y1="80"
                x2="260"
                y2="140"
                className="stroke-muted/40"
                strokeWidth="1"
              />
              <line
                x1="260"
                y1="140"
                x2="180"
                y2="240"
                className="stroke-muted/40"
                strokeWidth="1"
              />
              <line
                x1="120"
                y1="80"
                x2="180"
                y2="240"
                className="stroke-muted/30"
                strokeWidth="1"
                strokeDasharray="4 3"
              />
              <line
                x1="60"
                y1="180"
                x2="120"
                y2="80"
                className="stroke-muted/30"
                strokeWidth="1"
              />
              <line
                x1="320"
                y1="60"
                x2="260"
                y2="140"
                className="stroke-muted/30"
                strokeWidth="1"
              />
            </svg>

            {/* Faux nodes */}
            <div className="absolute left-[100px] top-[60px]">
              <Skeleton className="h-10 w-32 rounded-xl" />
            </div>
            <div className="absolute left-[240px] top-[120px]">
              <Skeleton className="h-10 w-28 rounded-xl" />
            </div>
            <div className="absolute left-[160px] top-[220px]">
              <Skeleton className="h-10 w-36 rounded-xl" />
            </div>
            <div className="absolute left-[40px] top-[160px]">
              <Skeleton className="h-10 w-24 rounded-xl" />
            </div>
            <div className="absolute left-[300px] top-[40px]">
              <Skeleton className="h-10 w-20 rounded-xl" />
            </div>
          </div>
        </div>

        {/* Loading text */}
        <div className="absolute inset-x-0 bottom-8 text-center">
          <p className="text-sm font-medium text-muted-foreground animate-pulse">
            Building knowledge graph…
          </p>
        </div>
      </div>
    </div>
  );
}
