"use client";
import { useState } from "react";
import AnswerCard from "./AnswerCard";
import type { AskResponse } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AskForm() {
  const [question, setQuestion] = useState("");
  const [results, setResults] = useState<AskResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    const submittedQuestion = question.trim();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: submittedQuestion }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Request failed");
      }
      const nextResult = await res.json();
      setResults((current) => [nextResult, ...current]);
      setQuestion("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={submit} className="flex gap-2 mb-6">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What is the refund policy?"
          className="flex-1 border rounded px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
        >
          {loading ? "..." : "Ask"}
        </button>
      </form>
      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
      <div className="space-y-6">
        {results.map((result, i) => (
          <section key={`${result.question}-${i}`} className="space-y-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Question
            </p>
            <p className="text-sm">{result.question}</p>
            <AnswerCard result={result} />
          </section>
        ))}
      </div>
    </div>
  );
}
