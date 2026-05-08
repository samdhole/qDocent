type Props = {
  result: {
    answer: string;
    citations: { document: string; page?: number; section?: string }[];
    retrieved_contexts: { text: string; score: number }[];
    confidence_label: string;
    needs_human_review: boolean;
  };
};

const LABEL_COLOR: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-red-100 text-red-800",
  needs_review: "bg-orange-100 text-orange-800",
};

export default function AnswerCard({ result }: Props) {
  return (
    <div className="space-y-4">
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
          <p className="text-xs text-orange-700 mt-1">⚠ Human review recommended</p>
        )}
      </div>

      {result.citations.length > 0 && (
        <div className="border rounded p-4">
          <p className="text-sm font-semibold text-gray-500 mb-2">Citations</p>
          <ul className="text-xs space-y-1">
            {result.citations.map((c, i) => (
              <li key={i}>
                {c.document} {c.page != null ? `· p.${c.page}` : ""}{" "}
                {c.section ? `· ${c.section}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.retrieved_contexts.length > 0 && (
        <div className="border rounded p-4">
          <p className="text-sm font-semibold text-gray-500 mb-2">Retrieved Chunks</p>
          {result.retrieved_contexts.map((ctx, i) => (
            <div key={i} className="mb-2 text-xs text-gray-700 border-l-2 pl-2">
              <span className="text-gray-400">score {ctx.score}</span>
              <p>{ctx.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
