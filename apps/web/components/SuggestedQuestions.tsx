// pattern: Imperative Shell
"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STATIC_SEEDS = [
  "What is the refund policy?",
  "Summarize the most important points across all documents.",
  "What deadlines are mentioned?",
] as const;

type SourceDocument = { document_id: string; source_file: string };

type Props = {
  onSelect: (question: string) => void;
  disabled?: boolean;
};

export function SuggestedQuestions({ onSelect, disabled }: Props) {
  const [docTitles, setDocTitles] = useState<string[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/documents`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : { documents: [] }))
      .then((d: { documents?: SourceDocument[] }) => {
        const titles = (d.documents ?? []).slice(0, 2).map((doc) => doc.source_file);
        setDocTitles(titles);
      })
      .catch(() => {
        // Silent — empty docs is the same as fetch failure for this surface.
      });
    return () => controller.abort();
  }, []);

  const docSuggestions = docTitles.map((t) => `Summarize ${t}`);
  const all = [...docSuggestions, ...STATIC_SEEDS].slice(0, 6);

  return (
    <div className="flex flex-wrap gap-2">
      {all.map((q) => (
        <Button
          key={q}
          variant="outline"
          size="sm"
          onClick={() => onSelect(q)}
          disabled={disabled}
          className="text-xs h-auto py-2 whitespace-normal text-left"
        >
          {q}
        </Button>
      ))}
    </div>
  );
}
