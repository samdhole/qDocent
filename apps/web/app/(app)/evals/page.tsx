import EvalTable from "@/components/EvalTable";

export default function EvalsPage() {
  return (
    <div className="max-w-3xl mx-auto p-6 md:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Evaluations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          RAGAS evaluation results for answer quality.
        </p>
      </header>
      <EvalTable />
    </div>
  );
}
