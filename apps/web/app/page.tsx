import Link from "next/link";

export default function HomePage() {
  return (
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">DocQuery</h1>
      <p className="text-gray-500 mb-8 text-sm">
        Local-first RAG demo — ask questions over your business documents.
      </p>
      <nav className="flex flex-col gap-3">
        <Link href="/ask" className="block border rounded p-4 hover:bg-gray-50">
          <span className="font-semibold">Ask a Question</span>
          <p className="text-xs text-gray-500 mt-1">Query ingested documents with RAG and see citations.</p>
        </Link>
        <Link href="/documents" className="block border rounded p-4 hover:bg-gray-50">
          <span className="font-semibold">Documents</span>
          <p className="text-xs text-gray-500 mt-1">Upload and ingest PDFs into R2R.</p>
        </Link>
        <Link href="/evals" className="block border rounded p-4 hover:bg-gray-50">
          <span className="font-semibold">Evaluations</span>
          <p className="text-xs text-gray-500 mt-1">RAGAS scores — faithfulness, relevancy, precision.</p>
        </Link>
      </nav>
    </main>
  );
}
