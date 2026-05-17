import { notFound } from "next/navigation";
import WikiPage from "@/components/WikiPage";
import WikiTreeNav, { WikiStructure } from "@/components/WikiTreeNav";
import ConversationView from "@/components/ConversationView";

const API_BASE = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  params: Promise<{ id: string; slug: string }>;
}

interface BackendSection {
  id: string;
  title: string;
  page_slugs: string[];
}

interface BackendPage {
  slug: string;
  title: string;
}

function joinStructure(
  backendStructure: { title: string; sections: BackendSection[] } | null,
  backendPages: BackendPage[],
): WikiStructure | null {
  if (!backendStructure) return null;
  const pageMap = new Map(backendPages.map((p) => [p.slug, p]));
  return {
    title: backendStructure.title,
    sections: backendStructure.sections.map((sec) => ({
      title: sec.title,
      pages: sec.page_slugs
        .map((slug) => pageMap.get(slug))
        .filter((p): p is BackendPage => Boolean(p))
        .map((p) => ({ slug: p.slug, title: p.title })),
    })),
  };
}

export default async function WikiSlugPage({ params }: Props) {
  const { id, slug } = await params;

  const [wikiResp, pageResp, docsResp] = await Promise.all([
    fetch(`${API_BASE}/notebooks/${id}/wiki`, { cache: "no-store" }),
    fetch(`${API_BASE}/notebooks/${id}/wiki/${slug}`, { cache: "no-store" }),
    fetch(`${API_BASE}/notebooks/${id}/documents`, { cache: "no-store" }),
  ]);

  if (!pageResp.ok) notFound();

  const wikiData = wikiResp.ok ? await wikiResp.json() : null;
  const structure: WikiStructure | null = joinStructure(
    wikiData?.structure ?? null,
    wikiData?.pages ?? [],
  );
  const page = (await pageResp.json()) as {
    slug: string;
    title: string;
    content: string;
    source_doc_ids: string[];
  };

  const docNames: Record<string, string> = {};
  if (docsResp.ok) {
    const docsData = await docsResp.json() as { documents?: { document_id: string; source_file: string }[] };
    for (const doc of docsData.documents ?? []) {
      // Store just the basename (e.g. "robinhood-ars.pdf" not full path)
      docNames[doc.document_id] = doc.source_file.split('/').at(-1) ?? doc.source_file;
    }
  }

  return (
    <div className="flex gap-8 p-6">
      {structure && (
        <WikiTreeNav notebookId={id} structure={structure} activeSlug={slug} />
      )}
      <div className="flex-1 min-w-0">
        <WikiPage
          title={page.title}
          content={page.content ?? ""}
          sourceDocIds={page.source_doc_ids ?? []}
          docNames={docNames}
        />
        <div className="border-t border-border pt-6 mt-8">
          <p className="text-sm font-medium text-muted-foreground mb-4">
            Ask about this page
          </p>
          <div className="h-[520px]">
            <ConversationView
              notebookId={id}
              documentIds={page.source_doc_ids ?? []}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
