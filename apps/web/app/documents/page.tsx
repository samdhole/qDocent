"use client";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function DocumentsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setStatus(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/ingest`, { method: "POST", body: form });
      const data = await res.json();
      setStatus(res.ok ? `Ingested: ${data.result}` : `Error: ${data.detail}`);
    } catch (err: unknown) {
      setStatus(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
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
    </main>
  );
}
