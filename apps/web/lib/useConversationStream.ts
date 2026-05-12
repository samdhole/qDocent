// pattern: Imperative Shell
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import type { AskResponse, ChatMessage, ConversationStartResponse } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const MESSAGES_KEY = "qdocent.messages";

export type StreamPhase = "idle" | "searching" | "found_results" | "generating";

export function useConversationStream() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem(MESSAGES_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as ChatMessage[];
        if (Array.isArray(parsed)) return parsed;
      }
    } catch {
      // Corrupt or unavailable storage starts a fresh visible history.
    }
    return [];
  });
  const [pending, setPending] = useState(false);
  const [phase, setPhase] = useState<StreamPhase>("idle");
  const [partialText, setPartialText] = useState("");
  const partialTextRef = useRef("");

  const reset = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setPartialText("");
    setPhase("idle");
    partialTextRef.current = "";
    try {
      localStorage.removeItem(MESSAGES_KEY);
    } catch {
      // Ignore storage errors on reset.
    }
  }, []);

  useEffect(() => {
    try {
      if (messages.length === 0) {
        localStorage.removeItem(MESSAGES_KEY);
        return;
      }
      localStorage.setItem(MESSAGES_KEY, JSON.stringify(messages));
    } catch {
      // Storage quota exceeded or unavailable.
    }
  }, [messages]);

  function appendPartial(text: string) {
    partialTextRef.current += text;
    setPartialText(partialTextRef.current);
  }

  function clearPartial() {
    partialTextRef.current = "";
    setPartialText("");
  }

  const sendMessage = useCallback(
    async (text: string, opts?: { docOnly?: boolean; documentIds?: string[] }) => {
      const trimmed = text.trim();
      if (!trimmed || pending) return;
      setPending(true);
      setPhase("searching");
      setPartialText("");
      partialTextRef.current = "";

      let activeConversationId = conversationId;
      try {
        if (!activeConversationId) {
          const res = await fetch(`${API}/conversations`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail ?? "Could not start conversation.");
          }
          const body = (await res.json()) as ConversationStartResponse;
          activeConversationId = body.conversation_id;
          setConversationId(activeConversationId);
        }

        const userMessage: ChatMessage = {
          role: "user",
          content: trimmed,
          id: `${Date.now()}-u`,
        };
        setMessages((prev) => [...prev, userMessage]);

        const res = await fetch(
          `${API}/conversations/${activeConversationId}/messages/stream`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: trimmed,
              ...(opts?.docOnly && { doc_only: true }),
              ...(opts?.documentIds?.length && { document_ids: opts.documentIds }),
            }),
          },
        );
        if (!res.ok || !res.body) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? `Stream request failed (${res.status}).`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalResult: AskResponse | null = null;

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // SSE frames are separated by `\n\n`. Drain the buffer of full frames.
          let separatorIdx = buffer.indexOf("\n\n");
          while (separatorIdx >= 0) {
            const frame = buffer.slice(0, separatorIdx);
            buffer = buffer.slice(separatorIdx + 2);
            separatorIdx = buffer.indexOf("\n\n");
            handleFrame(frame);
          }
        }
        // Drain any trailing frame (rare — server sends \n\n after final).
        if (buffer.trim().startsWith("data:")) {
          handleFrame(buffer);
        }

        function handleFrame(frame: string) {
          // Each frame is "data: <json>" (we send single-line JSON).
          const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!dataLine) return;
          const json = dataLine.slice(5).trim();
          if (!json) return;
          let event: Record<string, unknown>;
          try {
            event = JSON.parse(json);
          } catch {
            return;
          }
          if (event.type === "status") {
            setPhase((event.phase as StreamPhase) ?? "generating");
          } else if (event.type === "token" && typeof event.text === "string") {
            appendPartial(event.text as string);
          } else if (event.type === "final" && event.result) {
            finalResult = event.result as AskResponse;
          } else if (event.type === "error" && typeof event.detail === "string") {
            throw new Error(event.detail);
          }
        }

        if (!finalResult) {
          throw new Error("Stream ended without final answer.");
        }
        const assistantMessage: ChatMessage = {
          role: "assistant",
          id: `${Date.now()}-a`,
          result: finalResult,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err: unknown) {
        const accumulated = partialTextRef.current;
        if (accumulated.trim()) {
          const partialAssistant: ChatMessage = {
            role: "assistant",
            id: `${Date.now()}-a-partial`,
            result: {
              question: trimmed,
              answer: accumulated + "\n\n_[stream interrupted]_",
              citations: [],
              retrieved_contexts: [],
              figures: [],
              confidence_label: "low",
              needs_human_review: true,
            },
          };
          setMessages((prev) => [...prev, partialAssistant]);
        }
        toast.error(err instanceof Error ? err.message : "Stream failed.");
      } finally {
        setPending(false);
        setPhase("idle");
        clearPartial();
      }
    },
    [conversationId, pending],
  );

  return { conversationId, messages, pending, phase, partialText, sendMessage, reset };
}
