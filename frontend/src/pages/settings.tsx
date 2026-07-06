import { ServerCog, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <section>
        <Badge variant="outline">Workspace controls</Badge>
        <h1 className="mt-3 text-2xl font-semibold tracking-normal md:text-3xl">Settings</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          Configure presentation preferences and review production integration settings.
        </p>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Workspace appearance</CardTitle>
            <CardDescription>Theme controls are available instantly from the top navigation for all pages.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-2xl border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
              The current theme is persisted automatically and applies across the enterprise console.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Backend integration</CardTitle>
            <CardDescription>Frontend API contract used by the production RAG backend.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <SettingRow icon={ServerCog} label="Upload endpoint" value="POST /upload" />
            <SettingRow icon={SlidersHorizontal} label="Assistant endpoint" value="POST /api/ask" />
            <SettingRow icon={ShieldCheck} label="Grounding mode" value="Source-cited RAG" />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function SettingRow({ icon: Icon, label, value }: { icon: typeof ServerCog; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-3">
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="h-4 w-4" aria-hidden="true" />
        {label}
      </span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}
