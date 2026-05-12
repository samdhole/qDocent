"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ConversationView from "@/components/ConversationView";
import NotebookHeader from "@/components/NotebookHeader";
import { Dropzone } from "@/components/Dropzone";
import { Skeleton } from "@/components/ui/skeleton";
import type { Notebook } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function NotebookPage() {
  const params = useParams<{ id: string }>();
  const notebookId = params.id;
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!notebookId) return;
    fetch(`${API}/notebooks/${notebookId}`)
      .then((r) => {
        if (r.status === 404) { setNotFound(true); return null; }
        return r.json();
      })
      .then((data) => { if (data) setNotebook(data as Notebook); })
      .catch(console.error);
  }, [notebookId]);

  if (notFound) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Notebook not found.
      </div>
    );
  }

  if (!notebook) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <NotebookHeader notebook={notebook} />
      <div className="px-6 py-3 border-b">
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            Add documents to this notebook
          </summary>
          <div className="mt-2">
            <Dropzone
              onFiles={async (files) => {
                for (const file of files) {
                  const form = new FormData();
                  form.append("file", file);
                  await fetch(`${API}/notebooks/${notebookId}/documents`, {
                    method: "POST",
                    body: form,
                  });
                }
              }}
            />
          </div>
        </details>
      </div>
      <div className="flex-1 min-h-0">
        <ConversationView notebookId={notebookId} />
      </div>
    </div>
  );
}
