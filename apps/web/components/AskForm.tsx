"use client";
import { useState } from "react";
import AnswerCard from "./AnswerCard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AskResponse = {
  question: string;
  answer: string;
  citations: { document: string; page?: number; section?: string; chunk_id?: string }[];
  retrieved_contexts: { chunk_id?: string; text: string; score: number }[];
  confidence_label: "high" | "medium" | "low" | "needs_review";
  needs_human_review: boolean;
};

export default function AskForm() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Request failed");
      }
      setResult(await res.json());
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
      {result && <AnswerCard result={result} />}
    </div>
  );
}
