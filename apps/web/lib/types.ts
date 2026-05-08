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
