// pattern: Imperative Shell
"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, ArrowUp, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import AnswerCard from "@/components/AnswerCard";
import { useConversation } from "@/lib/useConversation";

export default function ConversationView() {
  const { messages, pending, sendMessage, reset } = useConversation();
  const [draft, setDraft] = useState("");
  const scrollEndRef = useRef<HTMLDivElement>(null);

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
        {messages.length === 0 && (
          <Card>
            <CardContent className="pt-6 text-sm text-muted-foreground">
              Ask a question about your ingested documents.
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
              <AnswerCard result={m.result} />
            </div>
          );
        })}

        {pending && (
          <div className="flex items-center text-sm text-muted-foreground gap-2">
            <Loader2 className="size-4 animate-spin" />
            Thinking…
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
    </div>
  );
}
