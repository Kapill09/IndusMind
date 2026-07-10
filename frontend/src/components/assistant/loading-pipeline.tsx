import { useState, useEffect } from "react";
import { Bot, CheckCircle2, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

const PIPELINE_STEPS = [
  "Parsing question...",
  "Searching vector database...",
  "Ranking chunks...",
  "Generating grounded answer...",
  "Preparing citations..."
];

export function LoadingPipeline() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    // Advance steps artificially to show progression
    const intervals = [800, 1500, 1200, 2500]; // Duration for each step
    let timeout: ReturnType<typeof setTimeout>;
    
    const runSequence = (stepIndex: number) => {
      if (stepIndex < intervals.length) {
        timeout = setTimeout(() => {
          setActiveStep(stepIndex + 1);
          runSequence(stepIndex + 1);
        }, intervals[stepIndex]);
      }
    };
    
    runSequence(0);
    
    return () => clearTimeout(timeout);
  }, []);

  return (
    <div className="flex items-start gap-3" role="status" aria-live="polite" aria-label="Assistant is generating an answer">
      <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-secondary text-secondary-foreground">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="w-full rounded-2xl border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div className="text-sm font-medium text-foreground">INDUS MIND is working</div>
          <Skeleton className="h-3 w-24" />
        </div>
        <div className="space-y-3">
          {PIPELINE_STEPS.map((step, index) => {
            const isCompleted = index < activeStep;
            const isActive = index === activeStep;
            const isPending = index > activeStep;
            
            return (
              <motion.div 
                key={step}
                initial={{ opacity: 0, x: -10 }}
                animate={{ 
                  opacity: isPending ? 0.4 : 1, 
                  x: 0 
                }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-3 relative"
              >
                {index < PIPELINE_STEPS.length - 1 && (
                  <div className={cn(
                    "absolute left-2 top-4 bottom-[-12px] w-[2px]",
                    isCompleted ? "bg-primary" : "bg-border"
                  )} />
                )}
                
                <div className="relative z-10 flex h-4 w-4 items-center justify-center rounded-full bg-card">
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden="true" />
                  ) : isActive ? (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
                  ) : (
                    <div className="h-2 w-2 rounded-full bg-border" />
                  )}
                </div>
                
                <span className={cn(
                  "text-xs font-medium",
                  isActive ? "text-foreground" : "text-muted-foreground"
                )}>
                  {step}
                </span>
              </motion.div>
            );
          })}
        </div>
        <div className="mt-5 space-y-2">
          <Skeleton className="h-3 w-11/12" />
          <Skeleton className="h-3 w-4/5" />
        </div>
      </div>
    </div>
  );
}
