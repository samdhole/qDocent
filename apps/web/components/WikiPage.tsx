// pattern: Imperative Shell
'use client';

import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ExternalLink } from 'lucide-react';
import MermaidDiagram from '@/components/MermaidDiagram';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface WikiPageProps {
  title: string;
  content: string;
  sourceDocIds: string[];
  docNames?: Record<string, string>;
}

export default function WikiPage({ title, content, sourceDocIds, docNames }: WikiPageProps) {
  const markdownComponents = {
    code({ className, children }: { className?: string; children?: React.ReactNode }) {
      const lang = /language-(\w+)/.exec(className ?? '')?.[1];
      if (lang === 'mermaid') {
        return <MermaidDiagram chart={String(children).trim()} />;
      }
      return <code className={className}>{children}</code>;
    },
    a({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
      if (href?.startsWith('/notebooks/')) {
        return <Link href={href} {...props}>{children}</Link>;
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
          {children}
        </a>
      );
    },
  };

  return (
    <div className="flex-1 min-w-0">
      <article className="prose prose-neutral dark:prose-invert max-w-none">
        <h1>{title}</h1>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={markdownComponents}
        >
          {content}
        </ReactMarkdown>
      </article>
      {sourceDocIds.length > 0 && (
        <div className="mt-6 pt-4 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground mb-2">SOURCE DOCUMENTS</p>
          <div className="flex flex-wrap gap-2">
            {sourceDocIds.map((id) => {
              const name = docNames?.[id] ?? `${id.slice(0, 8)}…`;
              const href = `${API}/documents/${id}/source`;
              return (
                <a
                  key={id}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-muted text-muted-foreground hover:text-foreground px-2 py-1 rounded font-mono transition-colors inline-flex items-center gap-1"
                >
                  {name}
                  <ExternalLink className="inline h-3 w-3 opacity-60" />
                </a>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
