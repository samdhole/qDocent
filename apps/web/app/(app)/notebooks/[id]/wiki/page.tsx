import { redirect } from "next/navigation";
import WikiGenerateButton from "@/components/WikiGenerateButton";
import WikiTreeNav, { WikiStructure } from "@/components/WikiTreeNav";

const API_BASE = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  params: Promise<{ id: string }>;
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

export default async function WikiHomePage({ params }: Props) {
  const { id } = await params;

  let structure: WikiStructure | null = null;
  try {
    const resp = await fetch(`${API_BASE}/notebooks/${id}/wiki`, {
      cache: "no-store",
    });
    if (resp.ok) {
      const data = await resp.json();
      structure = joinStructure(data.structure, data.pages ?? []);
    }
  } catch {
    // API unreachable — fall through to empty state
  }

  if (!structure) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <p className="text-muted-foreground text-sm">
          No wiki yet for this notebook.
        </p>
        <WikiGenerateButton notebookId={id} />
      </div>
    );
  }

  // Redirect to first page if structure has pages
  const firstSlug = structure.sections?.[0]?.pages?.[0]?.slug;
  if (firstSlug) {
    redirect(`/notebooks/${id}/wiki/${firstSlug}`);
  }

  // Fallback: structure exists but is empty (edge case)
  return (
    <div className="flex gap-8 p-6">
      <WikiTreeNav notebookId={id} structure={structure} />
      <p className="text-muted-foreground text-sm self-start">
        Select a page from the sidebar.
      </p>
    </div>
  );
}
