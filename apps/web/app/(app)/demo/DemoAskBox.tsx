"use client";

import { useEffect, useState } from "react";
import ConversationView from "@/components/ConversationView";
import AnswerCard from "@/components/AnswerCard";
import { Badge } from "@/components/ui/badge";
import type { AskResponse } from "@/lib/types";
import qaData from "./data/example_qa.json";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const cachedAnswer: AskResponse = qaData as AskResponse;

type HealthState = "loading" | "live" | "offline";

export function DemoAskBox() {
  const notebookId = process.env.NEXT_PUBLIC_DEMO_NOTEBOOK_ID ?? "";
  const [healthState, setHealthState] = useState<HealthState>(
    notebookId ? "loading" : "offline"
  );

  useEffect(() => {
    if (!notebookId) return;

    // fire-and-forget: AbortSignal.timeout(2000) bounds the work; setState-on-unmount is silent in React 19
    fetch(`${API}/health`, { signal: AbortSignal.timeout(2000) })
      .then((res) => {
        setHealthState(res.ok ? "live" : "offline");
      })
      .catch(() => setHealthState("offline"));
  }, [notebookId]);

  if (healthState === "loading") {
    return <div className="border rounded-lg p-4 bg-card h-24 animate-pulse" />;
  }

  if (healthState === "live") {
    return (
      <div className="border rounded-lg">
        <ConversationView notebookId={notebookId} />
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-4 bg-card space-y-3">
      <Badge variant="secondary">
        Live demo unavailable — showing cached example
      </Badge>
      <AnswerCard result={cachedAnswer} />
    </div>
  );
}
