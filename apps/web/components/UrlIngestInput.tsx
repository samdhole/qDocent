"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Props = {
  notebookId: string;
};

export function UrlIngestInput({ notebookId }: Props) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    const trimmed = url.trim();
    if (!trimmed) return;
    setLoading(true);
    try {
      const resp = await fetch(`${API}/notebooks/${notebookId}/ingest/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: trimmed }),
      });
      if (resp.ok) {
        toast.success("URL ingested successfully.");
        setUrl("");
      } else {
        toast.error(`Failed to ingest URL (${resp.status})`);
      }
    } catch {
      toast.error("Failed to ingest URL. Check your connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex gap-2 mt-3">
      <Input
        type="url"
        placeholder="https://example.com/article"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !loading) void handleSubmit();
        }}
        disabled={loading}
        className="flex-1"
      />
      <Button onClick={handleSubmit} disabled={loading || !url.trim()}>
        {loading ? "Ingesting…" : "Ingest URL"}
      </Button>
    </div>
  );
}
