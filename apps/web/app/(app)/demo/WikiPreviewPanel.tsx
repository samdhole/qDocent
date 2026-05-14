import WikiTreeNav, { type WikiStructure } from "@/components/WikiTreeNav";
import WikiPage from "@/components/WikiPage";
import wikiData from "./data/wiki_structure.json";

// Direct typed assignment — TypeScript structurally checks wikiData.sections against
// WikiStructure at build time. If wiki_structure.json sections don't have {title, pages},
// this fails the compile. No 'as' cast here (that would defeat the check).
const structure: WikiStructure = wikiData;
const firstPage = structure.sections[0]?.pages[0];
const firstPageContent: string = wikiData.first_page_content ?? "";

export function WikiPreviewPanel() {
  const notebookId = process.env.NEXT_PUBLIC_DEMO_NOTEBOOK_ID ?? "demo";
  return (
    <div className="flex gap-4 border rounded-lg p-4 bg-card">
      <div className="max-h-96 overflow-hidden">
        <WikiTreeNav notebookId={notebookId} structure={structure} />
      </div>
      {firstPage && (
        <div className="flex-1 min-w-0">
          <WikiPage
            title={firstPage.title}
            content={firstPageContent}
            sourceDocIds={[]}
          />
        </div>
      )}
    </div>
  );
}
