"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NOTEBOOK_ACCEPT } from "@/lib/acceptedTypes";
import { useBatchUpload } from "@/lib/useBatchUpload";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Step = "pick" | "name" | "progress" | "done";

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onImported: (notebookId: string) => void;
};

const VALID_EXTS = new Set(
  Object.values(NOTEBOOK_ACCEPT).flat()
);

function isValidFile(file: File): boolean {
  const parts = file.name.split(".");
  if (parts.length < 2) return false;
  const ext = "." + parts.pop()!.toLowerCase();
  return VALID_EXTS.has(ext);
}

export function FolderImportDialog({ open, onOpenChange, onImported }: Props) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>("pick");
  const [validFiles, setValidFiles] = useState<Array<File>>([]);
  const [filteredCount, setFilteredCount] = useState(0);
  const [notebookName, setNotebookName] = useState("");
  const [notebookDesc, setNotebookDesc] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [notebookId, setNotebookId] = useState<string | null>(null);

  const { items, total, done, failed, batchStatus, start } = useBatchUpload();

  // Auto-advance from progress to done
  useEffect(() => {
    if (batchStatus === "complete") {
      setStep("done");
    }
  }, [batchStatus]);

  // Reset on close
  const handleOpenChange = (v: boolean) => {
    if (batchStatus === "running") return; // AC1.9: block close during upload
    if (!v) {
      setStep("pick");
      setValidFiles([]);
      setFilteredCount(0);
      setNotebookName("");
      setNotebookDesc("");
      setCreateError(null);
      setNotebookId(null);
    }
    onOpenChange(v);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const all = Array.from(e.target.files ?? []);
    const valid = all.filter(isValidFile);
    const filtered = all.length - valid.length;
    setValidFiles(valid);
    setFilteredCount(filtered);

    // Prefill notebook name from folder
    if (valid.length > 0) {
      const rel = (valid[0] as File & { webkitRelativePath?: string }).webkitRelativePath ?? "";
      const folder = rel.split("/")[0] ?? "";
      setNotebookName(folder);
    }
  };

  const handleStartImport = async () => {
    if (!notebookName.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const resp = await fetch(`${API}/notebooks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: notebookName.trim(),
          description: notebookDesc.trim() || null,
        }),
      });
      if (!resp.ok) {
        setCreateError(`Failed to create notebook (${resp.status})`);
        return;
      }
      const nb = await resp.json() as { id: string };
      setNotebookId(nb.id);
      setStep("progress");
      start(validFiles, nb.id);
    } catch {
      setCreateError("Failed to create notebook. Check your connection.");
    } finally {
      setCreating(false);
    }
  };

  const handleGenerateWiki = () => {
    if (!notebookId) return;
    void fetch(`${API}/notebooks/${notebookId}/wiki`, { method: "POST" });
    handleOpenChange(false);
    onImported(notebookId);
  };

  const handleViewNotebook = () => {
    if (!notebookId) return;
    handleOpenChange(false);
    onImported(notebookId);
    router.push(`/notebooks/${notebookId}`);
  };

  const isRunning = batchStatus === "running";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        onInteractOutside={(e) => { if (isRunning) e.preventDefault(); }}
      >
        <DialogHeader>
          <DialogTitle>
            {step === "pick" && "Select Folder"}
            {step === "name" && "Name Your Notebook"}
            {step === "progress" && "Importing Files…"}
            {step === "done" && "Import Complete"}
          </DialogTitle>
          <DialogDescription className="sr-only">
            Import files from a local folder into a new notebook.
          </DialogDescription>
        </DialogHeader>

        {step === "pick" && (
          <div className="space-y-4 py-2">
            {/* webkitdirectory is non-standard — TS doesn't know it */}
            <input
              ref={inputRef}
              type="file"
              // @ts-expect-error webkitdirectory is non-standard
              webkitdirectory=""
              multiple
              className="hidden"
              onChange={handleFileChange}
            />
            <Button variant="outline" onClick={() => inputRef.current?.click()}>
              Choose Folder
            </Button>
            {validFiles.length > 0 && (
              <p className="text-sm text-muted-foreground">
                {validFiles.length} file{validFiles.length !== 1 ? "s" : ""} ready to import
                {filteredCount > 0 && ` · ${filteredCount} unsupported skipped`}
              </p>
            )}
          </div>
        )}

        {step === "name" && (
          <div className="space-y-3 py-2">
            <Input
              placeholder="Notebook name"
              value={notebookName}
              onChange={(e) => setNotebookName(e.target.value)}
              autoFocus
            />
            <Input
              placeholder="Description (optional)"
              value={notebookDesc}
              onChange={(e) => setNotebookDesc(e.target.value)}
            />
            {createError && (
              <p className="text-sm text-destructive">{createError}</p>
            )}
          </div>
        )}

        {step === "progress" && (
          <div className="space-y-3 py-2">
            <p className="text-sm font-medium">
              {done + failed} / {total}
              {failed > 0 && ` · ${failed} failed`}
            </p>
            {items.filter((i) => i.status === "failed").length > 0 && (
              <ul className="max-h-40 overflow-y-auto space-y-1 text-sm text-destructive">
                {items
                  .filter((i) => i.status === "failed")
                  .map((i) => (
                    <li key={i.id}>
                      {i.file.name}: {i.error ?? "Upload failed"}
                    </li>
                  ))}
              </ul>
            )}
          </div>
        )}

        {step === "done" && (
          <div className="space-y-2 py-2">
            <p className="text-sm text-muted-foreground">
              {done} ingested · {failed} failed
            </p>
          </div>
        )}

        <DialogFooter>
          {step === "pick" && (
            <>
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button
                disabled={validFiles.length === 0}
                onClick={() => setStep("name")}
              >
                Next
              </Button>
            </>
          )}

          {step === "name" && (
            <>
              <Button variant="outline" onClick={() => setStep("pick")}>
                Back
              </Button>
              <Button
                disabled={creating || !notebookName.trim()}
                onClick={handleStartImport}
              >
                {creating ? "Creating…" : "Start Import →"}
              </Button>
            </>
          )}

          {step === "progress" && (
            <>
              <Button variant="outline" disabled>
                Cancel
              </Button>
            </>
          )}

          {step === "done" && (
            <>
              <Button variant="outline" onClick={handleGenerateWiki}>
                Generate Wiki
              </Button>
              <Button onClick={handleViewNotebook}>View Notebook →</Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
