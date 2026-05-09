import AskForm from "@/components/AskForm";

export default function AskPage() {
  return (
    <div className="max-w-3xl mx-auto p-6 md:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Ask</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Query ingested documents with RAG.
        </p>
      </header>
      <AskForm />
    </div>
  );
}
