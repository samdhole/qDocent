// pattern: Imperative Shell
'use client';

import dynamic from 'next/dynamic';
import { useEffect, useId, useRef, useState } from 'react';

let mermaidInitialized = false;

function MermaidDiagramInner({ chart }: { chart: string }) {
  const rawId = useId();
  // useId() returns strings like ":r0:" — strip colons for valid HTML ID
  const diagramId = `mermaid-${rawId.replace(/:/g, '')}`;
  const [svg, setSvg] = useState('');
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isMounted = true;

    async function render() {
      const mermaid = (await import('mermaid')).default;
      if (!mermaidInitialized) {
        mermaid.initialize({ startOnLoad: false, theme: 'default' });
        mermaidInitialized = true;
      }
      try {
        const { svg: rendered, bindFunctions } = await mermaid.render(diagramId, chart);
        if (!isMounted) return;
        setSvg(rendered);
        setError(null);
        if (bindFunctions && containerRef.current) {
          queueMicrotask(() => {
            if (containerRef.current) bindFunctions(containerRef.current);
          });
        }
      } catch (err) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : 'Diagram render error');
        setSvg('');
      }
    }

    render();
    return () => {
      isMounted = false;
    };
  }, [chart, diagramId]);

  if (error) {
    return (
      <pre className="text-destructive text-xs whitespace-pre-wrap">
        {`Mermaid error: ${error}`}
      </pre>
    );
  }

  return (
    <div
      ref={containerRef}
      className="overflow-x-auto my-4"
      // biome-ignore lint/security/noDangerouslySetInnerHtml: intentional SVG injection from mermaid
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

// next/dynamic with ssr:false prevents mermaid from running during server rendering.
// mermaid accesses `document` and `window` at import time — SSR would crash.
const MermaidDiagram = dynamic(
  () => Promise.resolve(MermaidDiagramInner),
  { ssr: false },
);

export default MermaidDiagram;
