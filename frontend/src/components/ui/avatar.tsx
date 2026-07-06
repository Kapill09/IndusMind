import { UserRound } from "lucide-react";
import { cn } from "@/lib/utils";

export function Avatar({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex h-9 w-9 items-center justify-center rounded-full border border-border bg-secondary text-secondary-foreground",
        className,
      )}
      aria-label="User profile"
    >
      <UserRound className="h-4 w-4" aria-hidden="true" />
    </div>
  );
}
