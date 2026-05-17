"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, PlusCircle, FolderOpen } from "lucide-react";
import NotebookCard from "@/components/NotebookCard";
import { FolderImportDialog } from "@/components/FolderImportDialog";
import type { Notebook } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function NotebookGrid() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch(`${API}/notebooks`, { signal: ctrl.signal })
      .then((r) => r.json())
      .then((data: Notebook[]) => setNotebooks(data))
      .catch(console.error)
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const resp = await fetch(`${API}/notebooks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim(), description: newDesc.trim() || null }),
      });
      if (resp.ok) {
        setShowCreate(false);
        setNewName("");
        setNewDesc("");
        // Reload notebooks
        const reloadCtrl = new AbortController();
        fetch(`${API}/notebooks`, { signal: reloadCtrl.signal })
          .then((r) => r.json())
          .then((data: Notebook[]) => setNotebooks(data))
          .catch(console.error);
      } else {
        toast.error(`Failed to create notebook: ${resp.status}`);
      }
    } catch {
      toast.error("Failed to create notebook");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const resp = await fetch(`${API}/notebooks/${id}`, { method: "DELETE" });
      if (!resp.ok) {
        toast.error(`Failed to delete notebook: ${resp.status}`);
        return;
      }
      // Reload notebooks
      const reloadCtrl = new AbortController();
      fetch(`${API}/notebooks`, { signal: reloadCtrl.signal })
        .then((r) => r.json())
        .then((data: Notebook[]) => setNotebooks(data))
        .catch(console.error);
    } catch {
      toast.error("Failed to delete notebook");
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 p-6">
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-36 rounded-lg" />)}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Notebooks</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setImportOpen(true)}>
            <FolderOpen className="mr-2 h-4 w-4" /> 📂 Import Folder
          </Button>
          <Button onClick={() => setShowCreate(true)}>
            <PlusCircle className="mr-2 h-4 w-4" /> New Notebook
          </Button>
        </div>
      </div>

      {notebooks.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
          <BookOpen className="h-12 w-12 mb-4 opacity-40" />
          <p className="text-lg mb-2">No notebooks yet</p>
          <p className="text-sm">Create a notebook to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {notebooks.map((nb) => (
            <NotebookCard key={nb.id} notebook={nb} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Notebook</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input
              placeholder="Notebook name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
            <Input
              placeholder="Description (optional)"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={creating || !newName.trim()}>
              {creating ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <FolderImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onImported={(notebookId) => {
          setImportOpen(false);
          // Reload notebooks list to show newly created notebook
          const ctrl = new AbortController();
          fetch(`${API}/notebooks`, { signal: ctrl.signal })
            .then((r) => r.json())
            .then((data: Notebook[]) => setNotebooks(data))
            .catch(console.error);
        }}
      />
    </div>
  );
}
