import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
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

const pipelineSteps = [
  "Uploading",
  "Extracting text",
  "Chunking",
  "Metadata extraction",
  "Embedding generation",
  "Vector storage",
  "Completed",
];

export function UploadPage({ onUploaded }: UploadPageProps) {
  const { notify } = useToast();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [pipelineStage, setPipelineStage] = useState(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file, setProgress),
    onMutate: () => {
      setProgress(0);
      setPipelineStage(0);
      setStartedAt(Date.now());
    },
    onSuccess: (response) => {
      setProgress(100);
      setPipelineStage(pipelineSteps.length - 1);
      onUploaded(response);
      notify({
        tone: "success",
        title: "Document indexed",
        description: `${response.filename} is ready for grounded retrieval.`,
      });
    },
    onError: (error) => {
      setPipelineStage(0);
      notify({
        tone: "error",
        title: "Upload failed",
        description: error instanceof Error ? error.message : "The document could not be uploaded.",
      });
    },
  });

  const targetStage = (() => {
    if (uploadMutation.isSuccess) {
      return pipelineSteps.length - 1;
    }

    if (!uploadMutation.isPending) {
      return 0;
    }

    if (progress < 20) {
      return 0;
    }
    if (progress < 40) {
      return 1;
    }
    if (progress < 60) {
      return 2;
    }
    if (progress < 75) {
      return 3;
    }
    if (progress < 90) {
      return 4;
    }
    return 5;
  })();

  useEffect(() => {
    if (uploadMutation.isSuccess) {
      setPipelineStage(pipelineSteps.length - 1);
      setProgress(100);
      return;
    }

    if (!uploadMutation.isPending || pipelineStage >= targetStage) {
      return;
    }

    const timer = window.setTimeout(() => {
      setPipelineStage((current) => Math.min(current + 1, targetStage));
    }, 180);

    return () => window.clearTimeout(timer);
  }, [pipelineStage, targetStage, uploadMutation.isPending, uploadMutation.isSuccess]);

  const acceptFile = useCallback((file?: File) => {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      notify({ tone: "error", title: "Unsupported file", description: "Only PDF files can be uploaded." });
      return;
    }
    setProgress(0);
    setPipelineStage(0);
    setStartedAt(null);
    setSelectedFile(file);
  }, [notify]);

  const startUpload = () => {
    if (selectedFile) uploadMutation.mutate(selectedFile);
  };

  const result = uploadMutation.data;
  const elapsedSeconds = useMemo(() => {
    if (!startedAt) return 0;
    return Math.max(1, Math.round((Date.now() - startedAt) / 1000));
  }, [startedAt, result]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section>
        <Badge variant="outline">Document ingestion</Badge>
        <h1 className="mt-3 text-2xl font-semibold tracking-[-0.02em] md:text-3xl">Upload industrial knowledge</h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
          Add manuals, SOPs, maintenance logs, inspection reports, and technical PDFs to the grounded knowledge base.
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
                "flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed p-8 text-center transition-all duration-200",
                isDragging ? "border-primary bg-secondary/70" : "border-border bg-background hover:bg-muted/60",
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
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
                <UploadCloud className="h-7 w-7" aria-hidden="true" />
              </div>
              <h2 className="mt-4 text-base font-semibold">Drop a PDF here or browse</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                Use source documents with readable text for best retrieval quality and page citations.
              </p>
            </label>

            {selectedFile ? (
              <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
                <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-secondary-foreground">
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
                {(uploadMutation.isPending || progress > 0) && (
                  <div className="mt-4 space-y-3">
                    <Progress value={progress} />
                    <p className="text-xs text-muted-foreground">{progress}% complete</p>
                  </div>
                )}
              </div>
            ) : null}

            <div className="rounded-2xl border border-border bg-muted/40 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">Pipeline status</p>
                  <p className="text-xs text-muted-foreground">Each stage animates as the backend processes the PDF.</p>
                </div>
                <Badge variant="secondary">{pipelineStage + 1}/{pipelineSteps.length}</Badge>
              </div>
              <div className="mt-4 space-y-3">
                {pipelineSteps.map((step, index) => {
                  const isFinalCompleted = uploadMutation.isSuccess && index === pipelineSteps.length - 1;
                  const isComplete = index < pipelineStage || isFinalCompleted;
                  const isActive = index === pipelineStage && !uploadMutation.isSuccess;
                  return (
                    <motion.div
                      key={step}
                      initial={{ opacity: 0, x: 6 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.16 }}
                      className={cn(
                        "flex items-center gap-3 rounded-xl border px-3 py-2 text-sm",
                        isComplete ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-300" : "border-border bg-background",
                        isActive ? "shadow-sm" : "",
                      )}
                    >
                      <div className={cn(
                        "flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold",
                        isComplete ? "bg-emerald-600 text-white" : isActive ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
                      )}>
                        {isComplete ? <CheckCircle2 className="h-4 w-4" /> : index + 1}
                      </div>
                      <span>{step}</span>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ingestion result</CardTitle>
            <CardDescription>Status returned by the production backend.</CardDescription>
          </CardHeader>
          <CardContent>
            {!result && !uploadMutation.isError ? (
              <div className="rounded-2xl border border-dashed border-border bg-muted/40 p-5 text-sm text-muted-foreground">
                Upload a PDF to see parsed pages, chunks, vectors, collection status, and elapsed processing time.
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
                <ResultRow label="Time taken" value={`${elapsedSeconds}s`} />
                <ResultRow label="Collection" value={result.ingestion.collection} />
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
    <div className="flex gap-3 rounded-2xl border border-border bg-background p-4 shadow-sm">
      <div
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-xl",
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
    <div className="flex items-center justify-between rounded-xl border border-border bg-background/70 px-3 py-2">
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        <Layers3 className="h-4 w-4" aria-hidden="true" />
        {label}
      </span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}
