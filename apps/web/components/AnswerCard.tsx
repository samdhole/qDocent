import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

import type { AskResponse, SelectedCitation } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const LABEL_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  high: "default",
  medium: "secondary",
  low: "destructive",
  needs_review: "outline",
};

type Props = {
  result: AskResponse;
  onSelectCitation?: (citation: SelectedCitation) => void;
};

function sourceHref(documentId: string, page?: number) {
  return `${API}/documents/${encodeURIComponent(documentId)}/source${
    page != null ? `#page=${page}` : ""
  }`;
}

export default function AnswerCard({ result, onSelectCitation }: Props) {
  const isLowConfidenceNoContext =
    result.confidence_label === "low" && result.retrieved_contexts.length === 0;

  return (
    <div className="space-y-4">
      {isLowConfidenceNoContext && (
        <Card className="border-amber-300 bg-amber-50">
          <CardContent className="pt-4 text-sm text-amber-700">
            This question could not be answered from the available documents. The information
            may not be in the ingested content.
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
            <span>Answer</span>
            <Badge variant={LABEL_VARIANT[result.confidence_label] ?? "outline"} className="capitalize">
              {result.confidence_label.replace("_", " ")}
            </Badge>
            {result.needs_human_review && (
              <span className="text-xs text-orange-700">Human review recommended</span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>
        </CardContent>
      </Card>

      {result.citations.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Citations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="text-xs space-y-1">
              {result.citations.map((c, i) => {
                const label = `${c.document}${c.page != null ? ` · p.${c.page}` : ""}${
                  c.section ? ` · ${c.section}` : ""
                }`;
                return (
                  <li key={c.chunk_id != null ? `${c.document_id ?? "doc"}-${c.chunk_id}-${i}` : i}>
                    {c.document_id && onSelectCitation && c.page != null ? (
                      <button
                        type="button"
                        onClick={() =>
                          onSelectCitation({
                            documentId: c.document_id!,
                            documentName: c.document,
                            pageStart: c.page!,
                            pageEnd: c.page_end ?? null,
                            chunkIndex: c.chunk_index ?? null,
                          })
                        }
                        className="text-blue-700 hover:underline text-left"
                      >
                        {label}
                      </button>
                    ) : c.document_id ? (
                      <a
                        href={sourceHref(c.document_id, c.page ?? undefined)}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-700 hover:underline"
                      >
                        {label}
                      </a>
                    ) : (
                      label
                    )}
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      {result.figures.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Figures</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {result.figures.map((fig) => (
              <figure key={fig.figure_id} className="border rounded p-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`${API}${fig.image_url}`}
                  alt={fig.caption || fig.figure_id}
                  className="w-full rounded"
                />
                <figcaption className="text-xs text-muted-foreground mt-1">
                  {fig.caption || `${fig.source_file} · p.${fig.page_number}`}
                </figcaption>
              </figure>
            ))}
          </CardContent>
        </Card>
      )}

      {result.retrieved_contexts.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Retrieved Chunks
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {result.retrieved_contexts.map((ctx, i) => (
              <div
                key={ctx.chunk_id != null ? `${ctx.chunk_id}-${i}` : i}
                className="text-xs text-muted-foreground border-l-2 pl-2"
              >
                <span className="text-muted-foreground/70">score {ctx.score}</span>
                <p className="mt-1 text-foreground/80">{ctx.text}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
