"use client";
import { useEffect, useRef, useState } from "react";

import { Loader2, Trash2, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

import type { IngestJob } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type SourceDocument = {
  document_id: string;
  source_file: string;
  source_url: string;
  size_bytes: number;
  updated_at: string;
};

export default function DocumentsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [job, setJob] = useState<IngestJob | null>(null);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const pollAbortRef = useRef<AbortController | null>(null);

  async function readDocuments(signal?: AbortSignal) {
    const res = await fetch(`${API}/documents`, { signal });
    const data = await res.json();
    return res.ok ? data.documents ?? [] : [];
  }

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
  }, []);

  // Abort any in-flight poll on unmount. Active-upload abort is handled inside
  // upload() via pollAbortRef.current?.abort() before creating a new controller.
  useEffect(() => {
    return () => {
      pollAbortRef.current?.abort();
    };
  }, []);

  async function loadDocuments() {
    setLoadingDocuments(true);
    try {
      setDocuments(await readDocuments());
    } finally {
      setLoadingDocuments(false);
    }
  }

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setStatus(null);
    setSourceUrl(null);
    setJob(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/ingest/jobs`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) {
        setStatus(`Error: ${data.detail}`);
        setUploading(false);
        return;
      }
      setJob(data);
      setStatus(`Queued ingest job: ${data.job_id}`);
      // abort any previous poll
      pollAbortRef.current?.abort();
      const controller = new AbortController();
      pollAbortRef.current = controller;
      void pollJob(data.job_id, controller.signal);
    } catch (err: unknown) {
      setStatus(err instanceof Error ? err.message : "Upload failed");
      setUploading(false);
    }
  }

  async function pollJob(jobId: string, signal: AbortSignal) {
    const maxAttempts = 90;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      if (signal.aborted) return;
      try {
        const res = await fetch(`${API}/ingest/jobs/${jobId}`, { signal });
        if (signal.aborted) return;
        const nextJob = await res.json();
        if (signal.aborted) return;
        if (!res.ok) {
          setStatus(`Error: ${nextJob.detail ?? "Could not load ingest job."}`);
          setUploading(false);
          return;
        }
        setJob(nextJob);
        if (nextJob.status === "completed") {
          setStatus(`Ingested document ID: ${nextJob.result?.document_id ?? "OK"}`);
          setSourceUrl(nextJob.result?.source_url ? `${API}${nextJob.result.source_url}` : null);
          await loadDocuments();
          setUploading(false);
          return;
        }
        if (nextJob.status === "failed") {
          setStatus(`Error: ${nextJob.error ?? "Ingest failed."}`);
          setUploading(false);
          return;
        }
        await new Promise<void>((resolve) => {
          const onAbort = () => {
            signal.removeEventListener("abort", onAbort);
            clearTimeout(timer);
            resolve();
          };
          const timer = setTimeout(() => {
            signal.removeEventListener("abort", onAbort);
            resolve();
          }, 1000);
          signal.addEventListener("abort", onAbort);
        });
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        setStatus(`Error polling ingest job: ${String(err)}`);
        setUploading(false);
        return;
      }
    }
    setStatus("Ingest is still running. Refresh stored sources in a moment.");
    setUploading(false);
  }

  async function deleteDocument(documentId: string) {
    setConfirmingId(null);   // clear confirmation before starting
    setDeletingId(documentId);
    setStatus(null);
    try {
      const res = await fetch(`${API}/documents/${documentId}`, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) {
        setStatus(`Error: ${data.detail ?? "Delete failed."}`);
        return;
      }
      const r2rCount = Array.isArray(data.r2r_delete?.deleted)
        ? data.r2r_delete.deleted.length
        : 0;
      setStatus(
        r2rCount > 0
          ? `Deleted document ID ${data.document_id} and ${r2rCount} R2R record(s).`
          : `Deleted local source PDF for document ID: ${data.document_id}`
      );
      await loadDocuments();
    } catch (err: unknown) {
      setStatus(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 md:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Documents</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload a PDF to ingest it into R2R.
        </p>
      </header>

      <form onSubmit={upload} className="flex gap-2 mb-6">
        <Input
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <Button type="submit" disabled={uploading || !file}>
          {uploading ? (
            <>
              <Loader2 className="size-4 animate-spin mr-2" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="size-4 mr-2" />
              Ingest PDF
            </>
          )}
        </Button>
      </form>

      {status && (
        <Card className={status.startsWith("Error") ? "border-destructive/50 bg-destructive/5 mb-6" : "mb-6"}>
          <CardContent className="pt-4 text-sm">
            <p className={status.startsWith("Error") ? "text-destructive" : "text-green-700"}>
              {status}
            </p>
          </CardContent>
        </Card>
      )}

      {job && (
        <Card className="mb-6">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between gap-3 mb-3">
              <span className="font-medium text-sm">{job.filename}</span>
              <Badge variant="secondary">{job.status}</Badge>
            </div>
            <Progress
              value={
                job.status === "queued"
                  ? 20
                  : job.status === "running"
                    ? 60
                    : job.status === "failed"
                      ? 0
                      : 100
              }
            />
          </CardContent>
        </Card>
      )}

      {sourceUrl && (
        <div className="mb-6">
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-blue-700 hover:underline"
          >
            Open stored source PDF
          </a>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-muted-foreground">Stored Sources</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingDocuments ? (
            <p className="text-sm text-muted-foreground">Loading documents…</p>
          ) : documents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No stored source PDFs yet.</p>
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
