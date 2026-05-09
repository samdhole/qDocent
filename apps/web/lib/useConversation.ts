// pattern: Imperative Shell
import { useCallback, useState } from "react";
import { toast } from "sonner";

import type { AskResponse, ChatMessage, ConversationStartResponse } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useConversation() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);

  const reset = useCallback(() => {
    setConversationId(null);
    setMessages([]);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || pending) return;
      setPending(true);

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

        const res = await fetch(`${API}/conversations/${activeConversationId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: trimmed }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? "Request failed.");
        }
        const result = (await res.json()) as AskResponse;
        const assistantMessage: ChatMessage = {
          role: "assistant",
          id: `${Date.now()}-a`,
          result,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Unknown error.";
        toast.error(message);
      } finally {
        setPending(false);
      }
    },
    [conversationId, pending],
  );

  return { conversationId, messages, pending, sendMessage, reset };
}
