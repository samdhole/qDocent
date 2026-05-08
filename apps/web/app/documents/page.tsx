"use client";
import { useEffect, useRef, useState } from "react";
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
      const res = await fetch(`${API}/ingest/jobs/${jobId}`, { signal }).catch(() => null);
      if (res === null || signal.aborted) return;
      const nextJob = await res.json();
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
      await new Promise<void>((resolve, reject) => {
        const timer = setTimeout(resolve, 1000);
        signal.addEventListener("abort", () => { clearTimeout(timer); resolve(); });
      });
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
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Documents</h1>
      <p className="text-sm text-gray-500 mb-4">Upload a PDF to ingest it into R2R.</p>
      <form onSubmit={upload} className="flex gap-2 mb-4">
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="flex-1 text-sm"
        />
        <button
          type="submit"
          disabled={uploading || !file}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Ingest PDF"}
        </button>
      </form>
      {status && (
        <p className={`text-sm mt-2 ${status.startsWith("Error") ? "text-red-600" : "text-green-700"}`}>
          {status}
        </p>
      )}
      {job && (
        <div className="mt-3 border rounded p-3 text-sm">
          <div className="flex items-center justify-between gap-3">
            <span className="font-medium">{job.filename}</span>
            <span className="text-xs uppercase tracking-wide text-gray-500">{job.status}</span>
          </div>
          <div className="mt-2 h-2 rounded bg-gray-100 overflow-hidden">
            <div
              className={`h-full ${
                job.status === "failed" ? "bg-red-500" : "bg-blue-600"
              }`}
              style={{
                width:
                  job.status === "queued"
                    ? "20%"
                    : job.status === "running"
                      ? "60%"
                      : "100%",
              }}
            />
          </div>
        </div>
      )}
      {sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-blue-700 hover:underline"
        >
          Open stored source PDF
        </a>
      )}
      <section className="mt-8">
        <h2 className="text-sm font-semibold text-gray-500 mb-3">Stored Sources</h2>
        {loadingDocuments ? (
          <p className="text-sm text-gray-500">Loading documents...</p>
        ) : documents.length === 0 ? (
          <p className="text-sm text-gray-500">No stored source PDFs yet.</p>
        ) : (
          <div className="border rounded overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left font-medium p-2">Source</th>
                  <th className="text-left font-medium p-2">Document ID</th>
                  <th className="text-right font-medium p-2">Size</th>
                  <th className="text-right font-medium p-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.document_id} className="border-t">
                    <td className="p-2">
                      <a
                        href={`${API}${doc.source_url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-700 hover:underline"
                      >
                        {doc.source_file}
                      </a>
                    </td>
                    <td className="p-2 text-xs text-gray-500">{doc.document_id}</td>
                    <td className="p-2 text-right text-xs text-gray-500">
                      {Math.ceil(doc.size_bytes / 1024)} KB
                    </td>
                    <td className="p-2 text-right">
                      {confirmingId === doc.document_id ? (
                        <span className="flex justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => void deleteDocument(doc.document_id)}
                            disabled={deletingId === doc.document_id}
                            className="border rounded px-2 py-1 text-xs text-red-700 bg-red-50 hover:bg-red-100 disabled:opacity-50"
                          >
                            {deletingId === doc.document_id ? "Deleting..." : "Confirm?"}
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmingId(null)}
                            className="border rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-50"
                          >
                            Cancel
                          </button>
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmingId(doc.document_id)}
                          disabled={deletingId !== null}
                          className="border rounded px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
