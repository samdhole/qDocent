export type Citation = {
  document_id?: string;
  document: string;
  page?: number;
  page_end?: number;
  section?: string;
  chunk_id?: string;
  chunk_index?: number | null;
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
  doc_only_not_found?: boolean;
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

// Source panel types (added in Phase 7)

export type ChunkManifestEntry = {
  chunk_index: number;
  page_start: number | null;
  page_end: number | null;
  bbox: [number, number, number, number] | null; // [x0, top, x1, bottom] in points
  section_path: string | null;
  text_preview: string;
};

export type ChunksResponse = {
  document_id: string;
  chunks: ChunkManifestEntry[];
};

export type SelectedCitation = {
  documentId: string;
  documentName: string;
  pageStart: number;
  pageEnd: number | null;
  chunkIndex: number | null;
};
