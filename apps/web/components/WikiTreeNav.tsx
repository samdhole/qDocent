// pattern: Functional Core
import Link from 'next/link';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

export interface WikiPage {
  slug: string;
  title: string;
}

export interface WikiSection {
  title: string;
  pages: WikiPage[];
}

export interface WikiStructure {
  title: string;
  sections: WikiSection[];
}

interface WikiTreeNavProps {
  notebookId: string;
  structure: WikiStructure;
  activeSlug?: string;
}

export default function WikiTreeNav({
  notebookId,
  structure,
  activeSlug,
}: WikiTreeNavProps) {
  return (
    <nav className="w-56 shrink-0">
      <p className="font-semibold text-sm mb-3 text-foreground truncate">
        {structure.title}
      </p>
      <Separator className="mb-3" />
      <ScrollArea className="h-[calc(100vh-12rem)]">
        {structure.sections.map((section, idx) => (
          <div key={`${section.title}-${idx}`} className="mb-5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1 px-1">
              {section.title}
            </p>
            <ul className="space-y-0.5">
              {section.pages.map((page) => (
                <li key={page.slug}>
                  <Link
                    href={`/notebooks/${notebookId}/wiki/${page.slug}`}
                    className={`block text-sm px-2 py-1.5 rounded-md transition-colors ${
                      activeSlug === page.slug
                        ? 'bg-accent text-accent-foreground font-medium'
                        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                    }`}
                  >
                    {page.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </ScrollArea>
    </nav>
  );
}
