// pattern: Imperative Shell
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CitationProvider } from "@/components/CitationContext";
import { CitationBadge } from "@/components/CitationBadge";
import { remarkCitationBadges } from "@/lib/remarkCitationBadges";

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
  onSwitchToGeneral?: () => void;
};

export default function AnswerCard({ result, onSelectCitation, onSwitchToGeneral }: Props) {
  const isLowConfidenceNoContext =
    result.confidence_label === "low" && result.retrieved_contexts.length === 0;

  const isDocOnlyNotFound = Boolean(result.doc_only_not_found);

  const markdownComponents = {
    "cite-ref": ({ "data-num": num }: { "data-num"?: string }) => (
      <CitationBadge variant="inline" index={Number(num)} />
    ),
  } as unknown as Components;

  return (
    <CitationProvider
      citations={result.citations}
      retrievedContexts={result.retrieved_contexts}
      onSelectCitation={onSelectCitation}
    >
      <div className="space-y-4">
        {(isLowConfidenceNoContext || isDocOnlyNotFound) && (
          <Card className="border-amber-300 bg-amber-50">
            <CardContent className="pt-4 text-sm text-amber-700 space-y-2">
              <p>
                {isDocOnlyNotFound
                  ? "I couldn't find this in your documents."
                  : "This question could not be answered from the available documents. The information may not be in the ingested content."}
              </p>
              {isDocOnlyNotFound && onSwitchToGeneral && (
                <button
                  type="button"
                  onClick={onSwitchToGeneral}
                  className="text-amber-800 underline hover:text-amber-900 text-xs font-medium"
                >
                  Switch to General knowledge to broaden →
                </button>
              )}
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
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkCitationBadges]}
              components={markdownComponents}
            >
              {result.answer}
            </ReactMarkdown>
          </CardContent>
        </Card>

        {result.citations.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-muted-foreground">Citations</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {result.citations.map((c, i) => (
                <CitationBadge
                  key={c.chunk_id != null ? `${c.document_id ?? "doc"}-${c.chunk_id}-${i}` : i}
                  variant="panel"
                  index={i + 1}
                />
              ))}
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
    </CitationProvider>
  );
}
