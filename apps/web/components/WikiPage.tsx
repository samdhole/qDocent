// pattern: Functional Core
'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import MermaidDiagram from '@/components/MermaidDiagram';

interface WikiPageProps {
  title: string;
  content: string;
  sourceDocIds: string[];
}

export default function WikiPage({ title, content, sourceDocIds }: WikiPageProps) {
  return (
    <div className="flex-1 min-w-0">
      <article className="prose prose-neutral dark:prose-invert max-w-none">
        <h1>{title}</h1>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ className, children }) {
              const lang = /language-(\w+)/.exec(className ?? '')?.[1];
              if (lang === 'mermaid') {
                return <MermaidDiagram chart={String(children).trim()} />;
              }
              return <code className={className}>{children}</code>;
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </article>
      {sourceDocIds.length > 0 && (
        <div className="mt-6 pt-4 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground mb-2">SOURCE DOCUMENTS</p>
          <div className="flex flex-wrap gap-2">
            {sourceDocIds.map((id) => (
              <span
                key={id}
                className="text-xs bg-muted text-muted-foreground px-2 py-1 rounded font-mono"
              >
                {id.slice(0, 12)}&hellip;
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
