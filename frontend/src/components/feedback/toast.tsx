/* eslint-disable react-refresh/only-export-components */
import * as React from "react";
import { CheckCircle2, Info, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastTone = "success" | "error" | "info";

interface Toast {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
}

interface ToastContextValue {
  notify: (toast: Omit<Toast, "id">) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const notify = React.useCallback((toast: Omit<Toast, "id">) => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { ...toast, id }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 4200);
  }, []);

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-[min(380px,calc(100vw-2rem))] flex-col gap-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={cn(
              "rounded-lg border bg-card p-4 text-card-foreground shadow-enterprise",
              toast.tone === "success" && "border-emerald-200 dark:border-emerald-900",
              toast.tone === "error" && "border-red-200 dark:border-red-900",
            )}
          >
            <div className="flex gap-3">
              <ToastIcon tone={toast.tone} />
              <div>
                <p className="text-sm font-semibold">{toast.title}</p>
                {toast.description ? (
                  <p className="mt-1 text-sm text-muted-foreground">{toast.description}</p>
                ) : null}
              </div>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastIcon({ tone }: { tone: ToastTone }) {
  const className = "mt-0.5 h-4 w-4 shrink-0";
  if (tone === "success") return <CheckCircle2 className={cn(className, "text-emerald-600")} />;
  if (tone === "error") return <XCircle className={cn(className, "text-red-600")} />;
  return <Info className={cn(className, "text-primary")} />;
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}
