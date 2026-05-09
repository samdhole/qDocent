import Link from "next/link";
import { ArrowRight, MessageSquareText, FileText, Workflow, BarChart3 } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const ROUTES = [
  { href: "/ask", title: "Ask", icon: MessageSquareText, description: "Query ingested documents with cited answers and a source-side panel." },
  { href: "/documents", title: "Documents", icon: FileText, description: "Drag-drop ingest. Track progress. Manage your library." },
  { href: "/workflows", title: "Workflows", icon: Workflow, description: "Triage and approval-gated drafting via LangGraph." },
  { href: "/evals", title: "Evaluations", icon: BarChart3, description: "RAGAS scores: faithfulness, relevancy, precision." },
] as const;

export default function HomePage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-16 md:py-24">
      <header className="mb-12">
        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight">DocQuery</h1>
        <p className="text-muted-foreground mt-3 text-base md:text-lg max-w-2xl">
          Local-first RAG. Ingest your business documents, ask questions, and get cited answers
          with the original source pages right next to them.
        </p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        {ROUTES.map(({ href, title, description, icon: Icon }) => (
          <Card key={href} className="transition-colors hover:bg-accent/40">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icon className="size-5 text-muted-foreground" />
                {title}
              </CardTitle>
              <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="ghost" size="sm" className="-ml-3">
                <Link href={href}>
                  Open <ArrowRight className="size-4 ml-1" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
