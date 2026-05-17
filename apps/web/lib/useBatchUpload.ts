// pattern: Imperative Shell
import { useCallback, useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type BatchItem = {
  id: string;
  file: File;
  status: "pending" | "uploading" | "done" | "failed";
  error?: string;
};

type UseBatchUploadResult = {
  items: Array<BatchItem>;
  total: number;
  done: number;
  failed: number;
  batchStatus: "idle" | "running" | "complete";
  start: (files: Array<File>, notebookId: string) => void;
};

export function useBatchUpload(options?: {
  concurrency?: number;
}): UseBatchUploadResult {
  const concurrency = options?.concurrency ?? 4;
  const [items, setItems] = useState<Array<BatchItem>>([]);
  const [batchStatus, setBatchStatus] = useState<
    "idle" | "running" | "complete"
  >("idle");
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(
    (files: Array<File>, notebookId: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const snapshot: Array<BatchItem> = files.map((file) => ({
        id: crypto.randomUUID(),
        file,
        status: "pending",
      }));
      setItems(snapshot);
      setBatchStatus("running");

      // Per-invocation counters — safe because each start() creates a new closure scope.
      let index = 0;
      let inFlight = 0;
      let settled = 0;
      const total = snapshot.length;

      const uploadOne = async (item: BatchItem) => {
        setItems((prev) =>
          prev.map((i) =>
            i.id === item.id ? { ...i, status: "uploading" } : i
          )
        );

        try {
          const form = new FormData();
          form.append("file", item.file);
          const resp = await fetch(`${API}/notebooks/${notebookId}/documents`, {
            method: "POST",
            body: form,
            signal: controller.signal,
          });

          const success = resp.ok;
          const error = success ? undefined : `HTTP ${resp.status}`;
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? { ...i, status: success ? "done" : "failed", error }
                : i
            )
          );
        } catch (err) {
          if ((err as Error).name === "AbortError") return;
          const error =
            err instanceof Error ? err.message : "Upload failed";
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? { ...i, status: "failed", error }
                : i
            )
          );
        }

        inFlight -= 1;
        settled += 1;

        if (settled === total) {
          setBatchStatus("complete");
        } else {
          pump();
        }
      };

      const pump = () => {
        while (inFlight < concurrency && index < total) {
          const item = snapshot[index];
          index += 1;
          inFlight += 1;
          void uploadOne(item);
        }
      };

      pump();
    },
    [concurrency]
  );

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const done = items.filter((i) => i.status === "done").length;
  const failed = items.filter((i) => i.status === "failed").length;

  return { items, total: items.length, done, failed, batchStatus, start };
}
