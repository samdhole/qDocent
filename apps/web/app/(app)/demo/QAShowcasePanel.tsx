import AnswerCard from "@/components/AnswerCard";
import { type AskResponse } from "@/lib/types";
import qaData from "./data/example_qa.json";

const result: AskResponse = qaData as AskResponse;

export function QAShowcasePanel() {
  return (
    <div className="border rounded-lg p-4 bg-card">
      <p className="text-sm font-medium text-muted-foreground mb-3">
        Example Q&amp;A
      </p>
      <AnswerCard result={result} />
    </div>
  );
}
