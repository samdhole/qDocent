"use client";
import { useCallback, useEffect, useState } from "react";

import { Loader2, Trash2, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import { Dropzone } from "@/components/Dropzone";
import { UploadQueueList } from "@/components/UploadQueueList";
import { EmptyState } from "@/components/EmptyState";
import { useUploadQueue } from "@/lib/useUploadQueue";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type SourceDocument = {
  document_id: string;
  source_file: string;
  source_url: string;
  size_bytes: number;
  updated_at: string;
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const readDocuments = useCallback(async (signal?: AbortSignal) => {
    const res = await fetch(`${API}/documents`, { signal });
    const data = await res.json();
    return res.ok ? data.documents ?? [] : [];
  }, []);

  const loadDocuments = useCallback(async () => {
    setLoadingDocuments(true);
    try {
      setDocuments(await readDocuments());
    } finally {
      setLoadingDocuments(false);
    }
  }, [readDocuments]);

  useEffect(() => {
    const controller = new AbortController();
    readDocuments(controller.signal)
      .then(setDocuments)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name !== "AbortError") {
          setDocuments([]);
        }
      })
      .finally(() => setLoadingDocuments(false));
    return () => controller.abort();
  }, [readDocuments]);

  const { items, enqueue, removeItem } = useUploadQueue(loadDocuments);

  async function deleteDocument(documentId: string) {
    setConfirmingId(null);
    setDeletingId(documentId);
    try {
      const res = await fetch(`${API}/documents/${documentId}`, { method: "DELETE" });
      if (!res.ok) {
        return;
      }
      await loadDocuments();
    } catch {
      // silently handle errors
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 md:p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Documents</h1>
        <p className="text-sm text-muted-foreground mt-1">Drag and drop PDFs to ingest into R2R.</p>
      </header>

      <Dropzone onFiles={enqueue} />
      <UploadQueueList items={items} onRemove={removeItem} />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-muted-foreground">Stored Sources</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingDocuments ? (
            <p className="text-sm text-muted-foreground">Loading documents…</p>
          ) : documents.length === 0 ? (
            <EmptyState
              icon={Upload}
              title="No documents yet"
              body="Drop PDFs onto the area above to get started."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead>Document ID</TableHead>
                  <TableHead className="text-right">Size</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.document_id}>
                    <TableCell>
                      <a
                        href={`${API}${doc.source_url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-700 hover:underline"
                      >
                        {doc.source_file}
                      </a>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{doc.document_id}</TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {Math.ceil(doc.size_bytes / 1024)} KB
                    </TableCell>
                    <TableCell className="text-right">
                      {confirmingId === doc.document_id ? (
                        <div className="flex justify-end gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="destructive"
                            onClick={() => void deleteDocument(doc.document_id)}
                            disabled={deletingId === doc.document_id}
                          >
                            {deletingId === doc.document_id ? (
                              <>
                                <Loader2 className="size-3 animate-spin mr-1" />
                                Deleting...
                              </>
                            ) : (
                              "Confirm?"
                            )}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => setConfirmingId(null)}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          onClick={() => setConfirmingId(doc.document_id)}
                          disabled={deletingId !== null}
                        >
                          <Trash2 className="size-3 mr-1" />
                          Delete
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
