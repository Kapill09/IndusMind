import { Moon, ServerCog, ShieldCheck, SlidersHorizontal, Sun } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface SettingsPageProps {
  darkMode: boolean;
  setDarkMode: (value: boolean) => void;
}

export function SettingsPage({ darkMode, setDarkMode }: SettingsPageProps) {
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
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Switch between light and dark enterprise themes.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
                  {darkMode ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
                </div>
                <div>
                  <p className="text-sm font-semibold">Dark mode</p>
                  <p className="text-xs text-muted-foreground">Optimized for control rooms and long review sessions.</p>
                </div>
              </div>
              <Button variant={darkMode ? "default" : "outline"} onClick={() => setDarkMode(!darkMode)}>
                {darkMode ? "Enabled" : "Enable"}
              </Button>
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
