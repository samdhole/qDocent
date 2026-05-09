"use client";

import { useState } from "react";
import { Loader2, ArrowUp } from "lucide-react";

import AnswerCard from "./AnswerCard";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
    <div className="space-y-6">
      <form onSubmit={submit} className="flex gap-2">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What is the refund policy?"
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !question.trim()}>
          {loading ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
          <span className="sr-only">Ask</span>
        </Button>
      </form>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-4 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      <div className="space-y-6">
        {results.map((result, i) => (
          <section key={`${result.question}-${i}`} className="space-y-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
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
