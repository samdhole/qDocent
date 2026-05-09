// pattern: Imperative Shell
"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { Loader2, ArrowUp, Plus } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import AnswerCard from "@/components/AnswerCard";
import { SuggestedQuestions } from "@/components/SuggestedQuestions";
import { CitationBadge } from "@/components/CitationBadge";
import { CitationProvider } from "@/components/CitationContext";
import { remarkCitationBadges } from "@/lib/remarkCitationBadges";
import { useConversationStream } from "@/lib/useConversationStream";
import type { StreamPhase } from "@/lib/useConversationStream";
import type { SelectedCitation } from "@/lib/types";

// Lazy-load: pdfjs is heavy (~80kb gz). Only loads when a citation is clicked.
const SourcePanel = dynamic(() => import("@/components/SourcePanel"), {
  ssr: false,
  loading: () => null,
});

function phaseLabel(phase: StreamPhase): string {
  switch (phase) {
    case "searching": return "Searching documents…";
    case "found_results": return "Reading citations…";
    case "generating": return "Generating answer…";
    default: return "Thinking…";
  }
}

export default function ConversationView() {
  const { messages, pending, phase, partialText, sendMessage, reset } = useConversationStream();
  const [draft, setDraft] = useState("");
  const [selectedCitation, setSelectedCitation] = useState<SelectedCitation | null>(null);
  const scrollEndRef = useRef<HTMLDivElement>(null);

  const partialMarkdownComponents = {
    "cite-ref": ({ "data-num": num }: { "data-num"?: string }) => (
      <CitationBadge variant="inline" index={Number(num)} />
    ),
  } as unknown as Components;

  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    void sendMessage(text);
  }

  function onNewConversation() {
    reset();
    setDraft("");
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Ask</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={onNewConversation}
          disabled={messages.length === 0 || pending}
        >
          <Plus className="size-4 mr-1" /> New conversation
        </Button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto space-y-6 pr-2">
        {messages.length === 0 && !pending && (
          <Card>
            <CardContent className="pt-6 space-y-4">
              <p className="text-sm text-muted-foreground">
                Ask a question about your ingested documents, or pick one to start:
              </p>
              <SuggestedQuestions onSelect={(q) => void sendMessage(q)} disabled={pending} />
            </CardContent>
          </Card>
        )}

        {messages.map((m) => {
          if (m.role === "user") {
            return (
              <div key={m.id} className="flex justify-end">
                <div className="bg-primary text-primary-foreground rounded-lg px-3 py-2 text-sm max-w-[80%]">
                  {m.content}
                </div>
              </div>
            );
          }
          return (
            <div key={m.id}>
              <AnswerCard result={m.result} onSelectCitation={setSelectedCitation} />
            </div>
          );
        })}

        {pending && (
          <div className="space-y-2">
            <div className="flex items-center text-xs text-muted-foreground gap-2">
              <Loader2 className="size-3 animate-spin" />
              {phaseLabel(phase)}
            </div>
            {!partialText && (
              <div className="space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-4 w-5/6" />
              </div>
            )}
            {partialText && (
              <Card>
                <CardContent className="pt-4 text-sm prose prose-sm max-w-none">
                  <CitationProvider citations={[]} retrievedContexts={[]}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkCitationBadges]}
                      components={partialMarkdownComponents}
                    >
                      {partialText}
                    </ReactMarkdown>
                  </CitationProvider>
                </CardContent>
              </Card>
            )}
          </div>
        )}
        <div ref={scrollEndRef} />
      </div>

      <form onSubmit={onSubmit} className="flex gap-2 mt-4 pt-4 border-t">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={messages.length === 0 ? "What is the refund policy?" : "Ask a follow-up…"}
          disabled={pending}
        />
        <Button type="submit" disabled={pending || !draft.trim()}>
          {pending ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
          <span className="sr-only">Send</span>
        </Button>
      </form>

      <SourcePanel citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
    </div>
  );
}
