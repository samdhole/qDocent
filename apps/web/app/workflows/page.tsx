"use client";

import { useState } from "react";
import type { WorkflowResponse } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type WorkflowMode = "triage" | "email";

const MODES: Record<
  WorkflowMode,
  { label: string; endpoint: string; placeholder: string }
> = {
  triage: {
    label: "Support triage",
    endpoint: "/workflows/support/triage",
    placeholder: "A customer wants a refund after 45 days. Draft the next response.",
  },
  email: {
    label: "Email draft",
    endpoint: "/workflows/support/email-draft",
    placeholder: "Write a polite reply explaining the refund policy.",
  },
};

function approvalLabel(result: WorkflowResponse) {
  return result.requires_human_approval ? "Approval required" : "Ready to send";
}

export default function WorkflowsPage() {
  const [mode, setMode] = useState<WorkflowMode>("triage");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<WorkflowResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API}${MODES[mode].endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ?? "Workflow failed");
      }
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Workflow failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-5xl mx-auto p-8">
      <div className="mb-6">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          LangGraph workflow
        </p>
        <h1 className="text-2xl font-bold">Support Automation Review</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <section className="space-y-4">
          <div className="flex rounded border overflow-hidden text-sm">
            {(["triage", "email"] as WorkflowMode[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setMode(item)}
                className={`flex-1 px-3 py-2 ${
                  mode === item
                    ? "bg-gray-900 text-white"
                    : "bg-white text-gray-700 hover:bg-gray-50"
                }`}
              >
                {MODES[item].label}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-3">
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={MODES[mode].placeholder}
              className="w-full min-h-44 border rounded px-3 py-2 text-sm resize-y"
            />
            <button
              type="submit"
              disabled={loading || !message.trim()}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
            >
              {loading ? "Running..." : "Run workflow"}
            </button>
          </form>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </section>

        <section className="min-h-96 border rounded p-4">
          {!result ? (
            <div className="h-full flex items-center justify-center text-sm text-gray-500">
              Run a workflow to review the approval gate, draft output, and retrieval context.
            </div>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="border rounded px-2 py-1">
                  Intent: {result.intent || "general"}
                </span>
                <span className="border rounded px-2 py-1">
                  Confidence: {result.confidence_label}
                </span>
                <span
                  className={`rounded px-2 py-1 ${
                    result.requires_human_approval
                      ? "bg-amber-100 text-amber-900"
                      : "bg-green-100 text-green-900"
                  }`}
                >
                  {approvalLabel(result)}
                </span>
              </div>

              <div>
                <h2 className="text-sm font-semibold mb-2">Draft</h2>
                <pre className="whitespace-pre-wrap rounded bg-gray-50 p-3 text-sm">
                  {result.draft_response || result.final_response}
                </pre>
              </div>

              <div>
                <h2 className="text-sm font-semibold mb-2">Final response</h2>
                <p className="rounded border p-3 text-sm">
                  {result.final_response || "No final response returned."}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h2 className="text-sm font-semibold mb-2">Citations</h2>
                  {result.citations.length === 0 ? (
                    <p className="text-sm text-gray-500">No citations returned.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {result.citations.map((citation, i) => (
                        <li key={`${citation.document}-${i}`} className="border rounded p-2">
                          <span className="font-medium">{citation.document}</span>
                          {citation.page && (
                            <span className="text-gray-500"> page {citation.page}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div>
                  <h2 className="text-sm font-semibold mb-2">Retrieved context</h2>
                  {result.retrieved_contexts.length === 0 ? (
                    <p className="text-sm text-gray-500">No context returned.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {result.retrieved_contexts.slice(0, 3).map((context, i) => (
                        <li key={`${context.chunk_id ?? "context"}-${i}`} className="border rounded p-2">
                          <p className="text-xs text-gray-500 mb-1">Score {context.score}</p>
                          <p>{context.text}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
