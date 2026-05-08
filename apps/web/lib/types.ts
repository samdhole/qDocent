export type Citation = {
  document: string;
  page?: number;
  section?: string;
  chunk_id?: string;
};

export type RetrievedContext = {
  chunk_id?: string;
  text: string;
  score: number;
};

export type AskResponse = {
  question: string;
  answer: string;
  citations: Citation[];
  retrieved_contexts: RetrievedContext[];
  confidence_label: "high" | "medium" | "low" | "needs_review";
  needs_human_review: boolean;
};
