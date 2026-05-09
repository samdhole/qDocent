// pattern: Imperative Shell
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import type { IngestJob } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type UploadStatus = "queued" | "uploading" | "completed" | "failed";

/**
 * Pure module-scope function to process a single upload item.
 * Handles file upload and job polling without depending on hook state.
 */
async function processItem(
  item: UploadItem,
  deps: {
    updateItem: (id: string, patch: Partial<UploadItem>) => void;
    abortRef: React.MutableRefObject<AbortController | null>;
    onCompleted: () => void;
  },
): Promise<void> {
  const { updateItem, abortRef, onCompleted } = deps;
  updateItem(item.id, { status: "uploading", progress: 10 });
  abortRef.current = new AbortController();
  const signal = abortRef.current.signal;

  try {
    const form = new FormData();
    form.append("file", item.file);
    const submitRes = await fetch(`${API}/ingest/jobs`, {
      method: "POST",
      body: form,
      signal,
    });
    if (!submitRes.ok) {
      const err = await submitRes.json().catch(() => ({}));
      throw new Error(err.detail ?? `POST /ingest/jobs failed (${submitRes.status})`);
    }
    const job: IngestJob = await submitRes.json();
    updateItem(item.id, { progress: 30 });

    // Poll job until terminal status
    const finalJob = await pollJob(job.job_id, signal, (running) => {
      updateItem(item.id, { progress: running ? 60 : 30 });
    });

    if (finalJob.status === "completed") {
      updateItem(item.id, {
        status: "completed",
        progress: 100,
        documentId: finalJob.result?.document_id,
      });
      toast.success(`Ingested ${item.file.name}`);
      onCompleted();
    } else {
      updateItem(item.id, {
        status: "failed",
        progress: 100,
        error: finalJob.error ?? "Ingest failed",
      });
      toast.error(`Failed to ingest ${item.file.name}: ${finalJob.error ?? "unknown error"}`);
    }
  } catch (err: unknown) {
    // Swallow AbortError — cancelled uploads should silently stop, not show as failed
    if (err instanceof Error && err.name === "AbortError") {
      return;
    }
    const message = err instanceof Error ? err.message : "Upload failed.";
    updateItem(item.id, { status: "failed", progress: 100, error: message });
    toast.error(`Failed to upload ${item.file.name}: ${message}`);
  }
}

/**
 * Pure module-scope function to poll a job until terminal status.
 * No hook state dependencies; can be tested independently.
 */
async function pollJob(
  jobId: string,
  signal: AbortSignal,
  onTick: (running: boolean) => void,
): Promise<IngestJob> {
  const maxAttempts = 90;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (signal.aborted) throw new Error("Upload cancelled.");
    const res = await fetch(`${API}/ingest/jobs/${jobId}`, { signal });
    if (!res.ok) throw new Error(`Could not load ingest job (${res.status})`);
    const job: IngestJob = await res.json();
    if (job.status === "completed" || job.status === "failed") return job;
    onTick(job.status === "running");
    await new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, 1000);
      signal.addEventListener("abort", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
    });
  }
  throw new Error("Ingest still running after 90 polls. Try again later.");
}

export type UploadItem = {
  id: string;
  file: File;
  status: UploadStatus;
  progress: number; // 0-100, monotonic
  error?: string;
  documentId?: string;
};

type Listener = (items: UploadItem[]) => void;

export function useUploadQueue(onCompleted: () => void) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const queueRef = useRef<UploadItem[]>([]);
  const runningRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const unmountedRef = useRef(false);

  const setItemsAndRef: Listener = useCallback((next) => {
    queueRef.current = next;
    setItems(next);
  }, []);

  const updateItem = useCallback((id: string, patch: Partial<UploadItem>) => {
    setItemsAndRef(queueRef.current.map((it) => (it.id === id ? { ...it, ...patch } : it)));
  }, [setItemsAndRef]);

  const runIfIdle = useCallback(
    async () => {
      if (runningRef.current) return;
      runningRef.current = true;
      try {
        while (true) {
          // Stop processing queue if component unmounted
          if (unmountedRef.current) break;
          const next = queueRef.current.find((it) => it.status === "queued");
          if (!next) break;
          await processItem(next, { updateItem, abortRef, onCompleted });
        }
      } finally {
        runningRef.current = false;
      }
    },
    [updateItem, onCompleted],
  );

  const enqueue = useCallback((files: File[]) => {
    const newItems: UploadItem[] = files.map((f) => ({
      id: crypto.randomUUID(),
      file: f,
      status: "queued",
      progress: 0,
    }));
    setItemsAndRef([...queueRef.current, ...newItems]);
    void runIfIdle();
  }, [setItemsAndRef, runIfIdle]);

  /**
   * Only call for terminal items (completed/failed). Aborting an in-flight item is not supported — the X button is hidden for non-terminal states in UploadQueueList.
   */
  const removeItem = useCallback((id: string) => {
    setItemsAndRef(queueRef.current.filter((it) => it.id !== id));
  }, [setItemsAndRef]);


  // On unmount, abort in-flight fetch and stop queue processing
  useEffect(() => {
    unmountedRef.current = false;
    const abort = abortRef;
    return () => {
      unmountedRef.current = true;
      abort.current?.abort();
    };
  }, []);

  return { items, enqueue, removeItem };
}
