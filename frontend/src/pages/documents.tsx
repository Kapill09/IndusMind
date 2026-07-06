import { useMemo, useState } from "react";
import { FileText, Search, UploadCloud } from "lucide-react";
import { useToast } from "@/components/feedback/toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatNumber } from "@/lib/utils";
import type { KnowledgeDocument, PageKey } from "@/types";

interface DocumentsPageProps {
  documents: KnowledgeDocument[];
  onNavigate: (page: PageKey) => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
}

export function DocumentsPage({ documents, onNavigate, searchQuery, onSearchQueryChange }: DocumentsPageProps) {
  const { notify } = useToast();
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "pages" | "chunks">("newest");
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocument | null>(null);

  const filteredDocuments = useMemo(() => {
    const normalized = searchQuery.trim().toLowerCase();
    const list = normalized
      ? documents.filter((document) => document.filename.toLowerCase().includes(normalized))
      : documents;

    return [...list].sort((left, right) => {
      if (sortBy === "pages") return right.pages - left.pages;
      if (sortBy === "chunks") return right.chunks - left.chunks;
      if (sortBy === "oldest") return new Date(left.uploadedAt).getTime() - new Date(right.uploadedAt).getTime();
      return new Date(right.uploadedAt).getTime() - new Date(left.uploadedAt).getTime();
    });
  }, [documents, searchQuery, sortBy]);

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
              <CardDescription>Backend-backed ingestion history for this workspace.</CardDescription>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex w-full max-w-sm items-center gap-2 rounded-xl border border-input bg-background px-3 py-2">
                <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <Input
                  value={searchQuery}
                  onChange={(event) => onSearchQueryChange(event.target.value)}
                  className="border-0 px-0 focus-visible:ring-0"
                  placeholder="Search documents..."
                  aria-label="Search documents"
                />
              </div>
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value as "newest" | "oldest" | "pages" | "chunks")}
                className="rounded-xl border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="pages">Pages</option>
                <option value="chunks">Chunks</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredDocuments.length === 0 ? (
            <div className="flex min-h-56 flex-col items-center justify-center rounded-2xl border border-dashed border-border text-center">
              <FileText className="h-9 w-9 text-muted-foreground" aria-hidden="true" />
              <h2 className="mt-4 text-base font-semibold">No documents found</h2>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Upload a PDF or adjust your search to find indexed source material.
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-border">
              <div className="hidden grid-cols-[1.4fr_100px_100px_140px_110px_120px] gap-4 border-b border-border bg-muted/60 px-4 py-3 text-xs font-medium text-muted-foreground md:grid">
                <span>Filename</span>
                <span>Pages</span>
                <span>Chunks</span>
                <span>Upload date</span>
                <span>Status</span>
                <span>Actions</span>
              </div>
              <div className="divide-y divide-border">
                {filteredDocuments.map((document) => (
                  <DocumentRow
                    key={document.id}
                    document={document}
                    onView={() => setSelectedDocument(document)}
                    onExport={() => {
                      const payload = {
                        filename: document.filename,
                        pages: document.pages,
                        chunks: document.chunks,
                        vectors: document.vectors,
                        uploadedAt: document.uploadedAt,
                        status: document.status,
                      };
                      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
                      const url = window.URL.createObjectURL(blob);
                      const link = window.document.createElement("a");
                      link.href = url;
                      link.download = `${document.filename.replace(/\.[^.]+$/, "") || "document"}-metadata.json`;
                      link.click();
                      window.URL.revokeObjectURL(url);
                      notify({ tone: "success", title: "Export ready", description: `${document.filename} metadata was downloaded.` });
                    }}
                  />
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedDocument ? (
        <Card>
          <CardHeader>
            <CardTitle>{selectedDocument.filename}</CardTitle>
            <CardDescription>Document details for the indexed knowledge asset.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <DetailStat label="Pages" value={formatNumber(selectedDocument.pages)} />
            <DetailStat label="Chunks" value={formatNumber(selectedDocument.chunks)} />
            <DetailStat label="Vectors" value={formatNumber(selectedDocument.vectors)} />
            <DetailStat label="Uploaded" value={new Date(selectedDocument.uploadedAt).toLocaleString()} />
            <div className="md:col-span-2">
              <Button variant="outline" onClick={() => setSelectedDocument(null)}>
                Close details
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function DocumentRow({
  document,
  onView,
  onExport,
}: {
  document: KnowledgeDocument;
  onView: () => void;
  onExport: () => void;
}) {
  return (
    <div className="grid gap-3 px-4 py-4 text-sm md:grid-cols-[1.4fr_100px_100px_140px_110px_120px] md:items-center md:gap-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-secondary text-secondary-foreground">
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
      <div className="flex gap-2">
        <Button variant="ghost" size="sm" className="h-8 px-2 text-xs" onClick={onView}>
          View
        </Button>
        <Button variant="outline" size="sm" className="h-8 px-2 text-xs" onClick={onExport}>
          Export
        </Button>
      </div>
    </div>
  );
}

function DetailStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-background/70 p-3">
      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
