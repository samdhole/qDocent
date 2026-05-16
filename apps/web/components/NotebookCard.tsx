"use client";
import { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { BookOpen, Trash2 } from "lucide-react";
import type { Notebook } from "@/lib/types";

interface Props {
  notebook: Notebook;
  onDelete?: (id: string) => void;
}

export default function NotebookCard({ notebook, onDelete }: Props) {
  const [confirming, setConfirming] = useState(false);

  return (
    <Card className="hover:shadow-md transition-shadow relative">
      {/* Invisible overlaid link that makes the card area navigable without role="button" */}
      <Link
        href={`/notebooks/${notebook.id}`}
        className="absolute inset-0 z-0"
        aria-label={notebook.name}
        tabIndex={-1}
      />
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2 relative z-10">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-sm font-medium">{notebook.name}</CardTitle>
        </div>
        {onDelete && (
          confirming ? (
            <div className="flex items-center gap-1">
              <Button
                variant="destructive"
                size="sm"
                className="h-6 text-xs px-2"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(notebook.id); }}
              >
                Delete
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs px-2"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setConfirming(false); }}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-destructive"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); setConfirming(true); }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          )
        )}
      </CardHeader>
      <CardContent className="relative z-10">
        <CardDescription className="text-xs line-clamp-2">
          {notebook.description ?? "No description"}
        </CardDescription>
        {notebook.document_count !== undefined && (
          <p className="text-xs text-muted-foreground mt-1">
            {notebook.document_count} {notebook.document_count === 1 ? "document" : "documents"}
          </p>
        )}
        <Link href={`/notebooks/${notebook.id}`} className="mt-3 block relative z-20">
          <Button variant="outline" size="sm" className="w-full">Open</Button>
        </Link>
      </CardContent>
    </Card>
  );
}
