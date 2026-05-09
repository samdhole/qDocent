import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const ROUTES = [
  { href: "/ask", title: "Ask a Question", description: "Query ingested documents with RAG and see citations." },
  { href: "/documents", title: "Documents", description: "Upload and ingest PDFs into R2R." },
  { href: "/workflows", title: "Workflows", description: "Run support triage and approval-gated email drafts." },
  { href: "/evals", title: "Evaluations", description: "RAGAS scores for faithfulness, relevancy, and precision." },
] as const;

export default function HomePage() {
  return (
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">DocQuery</h1>
      <p className="text-muted-foreground mb-8 text-sm">
        Local-first RAG demo for asking questions over business documents.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {ROUTES.map((r) => (
          <Card key={r.href} className="transition-colors hover:bg-accent/50">
            <CardHeader>
              <CardTitle>{r.title}</CardTitle>
              <CardDescription>{r.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="secondary" size="sm">
                <Link href={r.href}>Open</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
