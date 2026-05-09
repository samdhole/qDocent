// pattern: Imperative Shell
"use client";
import { useEffect, useState } from "react";

import { BarChart3 } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Row = {
  question_id?: string;
  answer_relevancy?: number;
  context_precision?: number;
  faithfulness?: number;
  [key: string]: unknown;
};

const TARGETS: Record<string, number> = {
  faithfulness: 0.85,
  context_precision: 0.75,
  answer_relevancy: 0.80,
};

export default function EvalTable() {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState<{ message: string; isNotFound: boolean } | null>(null);

  useEffect(() => {
    fetch(`${API}/eval/results`)
      .then((r) => {
        if (!r.ok) {
          throw { message: r.status === 404 ? "No eval results yet. Run: make eval" : `HTTP ${r.status}: ${r.statusText}`, status: r.status };
        }
        return r.json();
      })
      .then(setRows)
      .catch((e: unknown) => {
        const isNetworkError = e instanceof TypeError;
        const status = typeof e === "object" && e !== null && "status" in e ? (e as { status: number }).status : null;
        const isNotFound = status === 404 || isNetworkError;
        const message = typeof e === "object" && e !== null && "message" in e
          ? (e as { message: string }).message
          : isNetworkError ? "Network error. Is the API running?" : "Unknown error";
        setError({ message, isNotFound });
      });
  }, []);

  if (error) {
    if (error.isNotFound) {
      return (
        <EmptyState
          icon={BarChart3}
          title="No evaluation reports yet"
          body="Run `make eval` from the project root to generate a RAGAS report. Reports appear here automatically."
        />
      );
    }
    return <p className="text-sm text-red-600">Error: {error.message}</p>;
  }
  if (!rows.length) return <p className="text-sm text-gray-500">Loading...</p>;

  const metrics = ["answer_relevancy", "context_precision", "faithfulness"];

  return (
    <div className="space-y-6">
      <table className="text-xs w-full border-collapse">
        <thead>
          <tr className="bg-gray-50">
            <th className="border px-2 py-1 text-left">Question ID</th>
            {metrics.map((m) => (
              <th key={m} className="border px-2 py-1 text-right">
                {m.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="border px-2 py-1">{row.question_id ?? i}</td>
              {metrics.map((m) => {
                const val = row[m] as number | undefined;
                const target = TARGETS[m] ?? 0;
                const pass = val != null && val >= target;
                return (
                  <td
                    key={m}
                    className={`border px-2 py-1 text-right ${
                      val == null ? "" : pass ? "text-green-700" : "text-red-600"
                    }`}
                  >
                    {val != null ? val.toFixed(3) : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-gray-50 font-semibold">
          <tr>
            <td className="border px-2 py-1">avg</td>
            {metrics.map((m) => {
              const vals = rows.map((r) => r[m] as number).filter((v) => v != null);
              const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
              const target = TARGETS[m] ?? 0;
              const pass = avg != null && avg >= target;
              return (
                <td
                  key={m}
                  className={`border px-2 py-1 text-right ${
                    avg == null ? "" : pass ? "text-green-700" : "text-red-600"
                  }`}
                >
                  {avg != null ? avg.toFixed(3) : "—"}
                </td>
              );
            })}
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
