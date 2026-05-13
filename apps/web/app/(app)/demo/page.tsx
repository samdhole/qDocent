import { WikiPreviewPanel } from "./WikiPreviewPanel";
import { QAShowcasePanel } from "./QAShowcasePanel";

export default function DemoPage() {
  return (
    <main className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Demo</h1>
        <p className="text-muted-foreground mt-1">
          DocQuery RAG pipeline — ingestion to cited answers.
        </p>
      </div>

      <section aria-labelledby="wiki-heading">
        <h2 id="wiki-heading" className="text-lg font-semibold mb-3">
          Wiki Generation
        </h2>
        <WikiPreviewPanel />
      </section>

      <section aria-labelledby="qa-heading">
        <h2 id="qa-heading" className="text-lg font-semibold mb-3">
          Cited Q&amp;A
        </h2>
        <QAShowcasePanel />
      </section>

      <section aria-labelledby="figure-heading">
        <h2 id="figure-heading" className="text-lg font-semibold mb-3">
          Figure Extraction
        </h2>
        <div className="border rounded-lg p-4 bg-card">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/demo/example_figure.png"
            alt="Extracted figure from 10-K filing"
            className="max-w-full rounded"
          />
          <p className="text-sm text-muted-foreground mt-2">
            Figure extracted from the demo 10-K corpus. Run{" "}
            <code className="text-xs bg-muted px-1 py-0.5 rounded">
              make demo-setup
            </code>{" "}
            to replace with a real figure.
          </p>
        </div>
      </section>

      <section aria-labelledby="ask-heading">
        <h2 id="ask-heading" className="text-lg font-semibold mb-3">
          Try It Live
        </h2>
        <div className="border rounded-lg p-4 bg-muted text-sm text-muted-foreground">
          Live ask box (implemented in Phase 3)
        </div>
      </section>
    </main>
  );
}
