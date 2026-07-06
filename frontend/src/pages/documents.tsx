import { useMemo, useState } from "react";
import { FileText, Search, UploadCloud } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatNumber } from "@/lib/utils";
import type { KnowledgeDocument, PageKey } from "@/types";

interface DocumentsPageProps {
  documents: KnowledgeDocument[];
  onNavigate: (page: PageKey) => void;
}

export function DocumentsPage({ documents, onNavigate }: DocumentsPageProps) {
  const [query, setQuery] = useState("");
  const filteredDocuments = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return documents;
    return documents.filter((document) => document.filename.toLowerCase().includes(normalized));
  }, [documents, query]);

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <Badge variant="outline">Knowledge library</Badge>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal md:text-3xl">Documents</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Review indexed PDFs and confirm the assistant has retrieval-ready source material.
          </p>
        </div>
        <Button onClick={() => onNavigate("upload")}>
          <UploadCloud className="h-4 w-4" aria-hidden="true" />
          Upload PDF
        </Button>
      </section>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle>Uploaded PDFs</CardTitle>
              <CardDescription>Locally tracked ingestion history for this workspace.</CardDescription>
            </div>
            <div className="flex w-full max-w-sm items-center gap-2 rounded-md border border-input bg-background px-3">
              <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="border-0 px-0 focus-visible:ring-0"
                placeholder="Search documents..."
                aria-label="Search documents"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredDocuments.length === 0 ? (
            <div className="flex min-h-56 flex-col items-center justify-center rounded-lg border border-dashed border-border text-center">
              <FileText className="h-9 w-9 text-muted-foreground" aria-hidden="true" />
              <h2 className="mt-4 text-base font-semibold">No documents found</h2>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Upload a PDF or adjust your search to find indexed source material.
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-border">
              <div className="hidden grid-cols-[1.5fr_120px_120px_160px_110px] gap-4 border-b border-border bg-muted/60 px-4 py-3 text-xs font-medium text-muted-foreground md:grid">
                <span>Filename</span>
                <span>Pages</span>
                <span>Chunks</span>
                <span>Upload date</span>
                <span>Status</span>
              </div>
              <div className="divide-y divide-border">
                {filteredDocuments.map((document) => (
                  <DocumentRow key={document.id} document={document} />
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function DocumentRow({ document }: { document: KnowledgeDocument }) {
  return (
    <div className="grid gap-3 px-4 py-4 text-sm md:grid-cols-[1.5fr_120px_120px_160px_110px] md:items-center md:gap-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
          <FileText className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate font-medium">{document.filename}</p>
          <p className="text-xs text-muted-foreground md:hidden">
            {formatNumber(document.pages)} pages · {formatNumber(document.chunks)} chunks
          </p>
        </div>
      </div>
      <span className="hidden text-muted-foreground md:block">{formatNumber(document.pages)}</span>
      <span className="hidden text-muted-foreground md:block">{formatNumber(document.chunks)}</span>
      <span className="text-xs text-muted-foreground md:text-sm">{new Date(document.uploadedAt).toLocaleDateString()}</span>
      <Badge variant={document.status === "indexed" ? "success" : "secondary"} className="w-fit capitalize">
        {document.status}
      </Badge>
    </div>
  );
}
