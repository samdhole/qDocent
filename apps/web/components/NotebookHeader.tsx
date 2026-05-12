"use client";
import { BookOpen } from "lucide-react";
import type { Notebook } from "@/lib/types";

interface Props {
  notebook: Notebook;
}

export default function NotebookHeader({ notebook }: Props) {
  return (
    <div className="flex items-center gap-3 px-6 py-4 border-b">
      <BookOpen className="h-5 w-5 text-muted-foreground shrink-0" />
      <div className="min-w-0">
        <h1 className="text-lg font-semibold truncate">{notebook.name}</h1>
        {notebook.description && (
          <p className="text-sm text-muted-foreground truncate">{notebook.description}</p>
        )}
      </div>
    </div>
  );
}
