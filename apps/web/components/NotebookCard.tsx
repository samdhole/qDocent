"use client";
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
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-sm font-medium">{notebook.name}</CardTitle>
        </div>
        {onDelete && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground hover:text-destructive"
            onClick={(e) => { e.preventDefault(); onDelete(notebook.id); }}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <CardDescription className="text-xs line-clamp-2">
          {notebook.description ?? "No description"}
        </CardDescription>
        <Link href={`/notebooks/${notebook.id}`} className="mt-3 block">
          <Button variant="outline" size="sm" className="w-full">Open</Button>
        </Link>
      </CardContent>
    </Card>
  );
}
