import { useCallback, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Layers3, Loader2, UploadCloud, XCircle } from "lucide-react";
import { uploadDocument } from "@/lib/api";
import { cn, fileSizeLabel, formatNumber } from "@/lib/utils";
import type { UploadResponse } from "@/types";
import { useToast } from "@/components/feedback/toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface UploadPageProps {
  onUploaded: (response: UploadResponse) => void;
}

export function UploadPage({ onUploaded }: UploadPageProps) {
  const { notify } = useToast();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file, setProgress),
    onSuccess: (response) => {
      onUploaded(response);
      notify({
        tone: "success",
        title: "Document indexed",
        description: `${response.filename} is ready for grounded retrieval.`,
      });
    },
    onError: (error) => {
      notify({
        tone: "error",
        title: "Upload failed",
        description: error instanceof Error ? error.message : "The document could not be uploaded.",
      });
    },
  });

  const acceptFile = useCallback((file?: File) => {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      notify({ tone: "error", title: "Unsupported file", description: "Only PDF files can be uploaded." });
      return;
    }
    setProgress(0);
    setSelectedFile(file);
  }, [notify]);

  const startUpload = () => {
    if (selectedFile) uploadMutation.mutate(selectedFile);
  };

  const result = uploadMutation.data;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section>
        <Badge variant="outline">Document ingestion</Badge>
        <h1 className="mt-3 text-2xl font-semibold tracking-normal md:text-3xl">Upload industrial knowledge</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          Add manuals, SOPs, maintenance logs, inspection reports, and technical PDFs to the RAG knowledge base.
        </p>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader>
            <CardTitle>PDF uploader</CardTitle>
            <CardDescription>Files are parsed, chunked, embedded, and stored in ChromaDB by the backend.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <label
              className={cn(
                "flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center transition-colors",
                isDragging ? "border-primary bg-secondary" : "border-border bg-background hover:bg-muted/60",
              )}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setIsDragging(false);
                acceptFile(event.dataTransfer.files[0]);
              }}
            >
              <input
                className="sr-only"
                type="file"
                accept="application/pdf,.pdf"
                onChange={(event) => acceptFile(event.target.files?.[0])}
                aria-label="Upload PDF document"
              />
              <div className="flex h-14 w-14 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
                <UploadCloud className="h-7 w-7" aria-hidden="true" />
              </div>
              <h2 className="mt-4 text-base font-semibold">Drop a PDF here or browse</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                Use source documents with readable text for best retrieval quality and page citations.
              </p>
            </label>

            {selectedFile ? (
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
                      <FileUp className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{selectedFile.name}</p>
                      <p className="text-xs text-muted-foreground">{fileSizeLabel(selectedFile.size)}</p>
                    </div>
                  </div>
                  <Button onClick={startUpload} disabled={uploadMutation.isPending}>
                    {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                    Ingest
                  </Button>
                </div>
                {uploadMutation.isPending || progress > 0 ? (
                  <div className="mt-4 space-y-2">
                    <Progress value={progress} />
                    <p className="text-xs text-muted-foreground">{progress}% uploaded</p>
                  </div>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ingestion result</CardTitle>
            <CardDescription>Status returned by the production backend.</CardDescription>
          </CardHeader>
          <CardContent>
            {!result && !uploadMutation.isError ? (
              <div className="rounded-lg border border-border bg-muted/40 p-5 text-sm text-muted-foreground">
                Upload a PDF to see parsed pages, chunks, vectors, and collection status.
              </div>
            ) : null}

            {uploadMutation.isError ? (
              <StatusPanel success={false} title="Ingestion failed" description="Review the API error and try again." />
            ) : null}

            {result ? (
              <div className="space-y-4">
                <StatusPanel success={result.success} title="Ingestion complete" description={result.ingestion.collection} />
                <ResultRow label="Pages" value={formatNumber(result.ingestion.pages)} />
                <ResultRow label="Chunks" value={formatNumber(result.ingestion.chunks)} />
                <ResultRow label="Vectors" value={formatNumber(result.ingestion.vectors)} />
                <ResultRow label="Status" value={result.ingestion.success ? "Ready" : "Failed"} />
              </div>
            ) : null}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function StatusPanel({
  success,
  title,
  description,
}: {
  success: boolean;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-3 rounded-lg border border-border bg-background p-4">
      <div
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-md",
          success ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40" : "bg-red-50 text-red-700 dark:bg-red-950/40",
        )}
      >
        {success ? <CheckCircle2 className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
      </div>
      <div>
        <p className="text-sm font-semibold">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function ResultRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border px-3 py-2">
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        <Layers3 className="h-4 w-4" aria-hidden="true" />
        {label}
      </span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}
