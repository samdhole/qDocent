import type { AskResponse } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const LABEL_COLOR: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-red-100 text-red-800",
  needs_review: "bg-orange-100 text-orange-800",
};

type Props = {
  result: AskResponse;
};

export default function AnswerCard({ result }: Props) {
  const isLowConfidenceNoContext =
    result.confidence_label === "low" && result.retrieved_contexts.length === 0;

  function sourceHref(documentId: string, page?: number) {
    return `${API}/documents/${encodeURIComponent(documentId)}/source${
      page != null ? `#page=${page}` : ""
    }`;
  }

  return (
    <div className="space-y-4">
      {isLowConfidenceNoContext && (
        <div className="border border-amber-300 rounded p-3 bg-amber-50">
          <p className="text-sm text-amber-700">
            This question could not be answered from the available documents.
            The information may not be in the ingested content.
          </p>
        </div>
      )}

      <div className="border rounded p-4">
        <p className="text-sm font-semibold text-gray-500 mb-1">Answer</p>
        <p className="text-sm">{result.answer}</p>
        <span
          className={`inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium ${
            LABEL_COLOR[result.confidence_label] ?? "bg-gray-100 text-gray-700"
          }`}
        >
          {result.confidence_label}
        </span>
        {result.needs_human_review && (
          <p className="text-xs text-orange-700 mt-1">Human review recommended</p>
        )}
      </div>

      {result.citations.length > 0 && (
        <div className="border rounded p-4">
          <p className="text-sm font-semibold text-gray-500 mb-2">Citations</p>
          <ul className="text-xs space-y-1">
            {result.citations.map((c, i) => {
              const label = `${c.document}${
                c.page != null ? ` · p.${c.page}` : ""
              }${c.section ? ` · ${c.section}` : ""}`;
              return (
                <li key={c.chunk_id ?? i}>
                  {c.document_id ? (
                    <a
                      href={sourceHref(c.document_id, c.page)}
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
        </div>
      )}

      {result.figures.length > 0 && (
        <div className="border rounded p-4">
          <p className="text-sm font-semibold text-gray-500 mb-2">Figures</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {result.figures.map((fig) => (
              <figure key={fig.figure_id} className="border rounded p-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`${API}${fig.image_url}`}
                  alt={fig.caption || fig.figure_id}
                  className="w-full rounded"
                />
                <figcaption className="text-xs text-gray-500 mt-1">
                  {fig.caption || `${fig.source_file} · p.${fig.page_number}`}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      )}

      {result.retrieved_contexts.length > 0 && (
        <div className="border rounded p-4">
          <p className="text-sm font-semibold text-gray-500 mb-2">
            Retrieved Chunks
          </p>
          {result.retrieved_contexts.map((ctx, i) => (
            <div
              key={ctx.chunk_id ?? i}
              className="mb-2 text-xs text-gray-700 border-l-2 pl-2"
            >
              <span className="text-gray-400">score {ctx.score}</span>
              <p>{ctx.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
