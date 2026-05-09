export type Citation = {
  document_id?: string;
  document: string;
  page?: number;
  page_end?: number;
  section?: string;
  chunk_id?: string;
};

export type RetrievedContext = {
  chunk_id?: string;
  text: string;
  score: number;
};

export type FigureAsset = {
  figure_id: string;
  source_file: string;
  page_number: number;
  image_url: string;
  caption?: string;
};

export type AskResponse = {
  question: string;
  answer: string;
  citations: Citation[];
  retrieved_contexts: RetrievedContext[];
  figures: FigureAsset[];
  confidence_label: "high" | "medium" | "low" | "needs_review";
  needs_human_review: boolean;
};

export type WorkflowResponse = {
  customer_message: string;
  intent: string;
  retrieved_contexts: RetrievedContext[];
  draft_response: string;
  citations: Citation[];
  confidence_label: "high" | "medium" | "low" | "needs_review";
  requires_human_approval: boolean;
  final_response: string;
};

export type IngestJob = {
  job_id: string;
  filename: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  result?: {
    document_id?: string;
    source_url?: string;
  } | null;
  error?: string | null;
};

// Conversation types (added in Phase 3)

export type ChatMessage =
  | { role: "user"; content: string; id: string }
  | { role: "assistant"; id: string; result: AskResponse };
// `result` is the existing AskResponse shape, returned by POST /conversations/{id}/messages.

export type ConversationStartResponse = {
  conversation_id: string;
};
