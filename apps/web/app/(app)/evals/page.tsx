import EvalTable from "@/components/EvalTable";

export default function EvalsPage() {
  return (
    <main className="max-w-5xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">RAGAS Evaluation Dashboard</h1>
      <EvalTable />
    </main>
  );
}
