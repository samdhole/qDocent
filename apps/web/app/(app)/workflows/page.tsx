"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
    <div className="max-w-3xl mx-auto p-6 md:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Workflows</h1>
        <p className="text-sm text-muted-foreground mt-1">
          LangGraph workflows for support automation.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <section className="space-y-4">
          <Tabs value={mode} onValueChange={(value) => setMode(value as WorkflowMode)}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="triage">Triage</TabsTrigger>
              <TabsTrigger value="email">Email</TabsTrigger>
            </TabsList>
          </Tabs>

          <form onSubmit={submit} className="space-y-3">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={MODES[mode].placeholder}
              className="h-32 p-3"
            />
            <Button type="submit" disabled={loading || !message.trim()} className="w-full">
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin mr-2" />
                  Running...
                </>
              ) : (
                "Run workflow"
              )}
            </Button>
          </form>
          {error && (
            <Card className="border-destructive/50 bg-destructive/5">
              <CardContent className="pt-4 text-sm text-destructive">{error}</CardContent>
            </Card>
          )}
        </section>

        <section>
          {!result ? (
            <Card className="min-h-96 flex items-center justify-center">
              <CardContent className="text-sm text-muted-foreground text-center">
                Run a workflow to review the approval gate, draft output, and retrieval context.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">Intent: {result.intent || "general"}</Badge>
                <Badge variant="outline">Confidence: {result.confidence_label}</Badge>
                <Badge
                  variant={
                    result.requires_human_approval ? "destructive" : "default"
                  }
                >
                  {approvalLabel(result)}
                </Badge>
              </div>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Draft</CardTitle>
                </CardHeader>
                <CardContent className="text-sm">
                  <pre className="whitespace-pre-wrap rounded bg-muted p-3">
                    {result.draft_response || result.final_response}
                  </pre>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Final response</CardTitle>
                </CardHeader>
                <CardContent className="text-sm">
                  {result.final_response || "No final response returned."}
                </CardContent>
              </Card>

              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Citations</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm">
                    {result.citations.length === 0 ? (
                      <p className="text-muted-foreground">No citations returned.</p>
                    ) : (
                      <ul className="space-y-2">
                        {result.citations.map((citation, i) => (
                          <li key={`${citation.document}-${i}`} className="border rounded p-2">
                            <span className="font-medium">{citation.document}</span>
                            {citation.page && (
                              <span className="text-muted-foreground"> page {citation.page}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Retrieved context</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm">
                    {result.retrieved_contexts.length === 0 ? (
                      <p className="text-muted-foreground">No context returned.</p>
                    ) : (
                      <ul className="space-y-2">
                        {result.retrieved_contexts.slice(0, 3).map((context, i) => (
                          <li key={`${context.chunk_id ?? "context"}-${i}`} className="border rounded p-2">
                            <p className="text-xs text-muted-foreground mb-1">Score {context.score}</p>
                            <p>{context.text}</p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
