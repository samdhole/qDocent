// pattern: Imperative Shell
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

type GenState = 'idle' | 'generating' | 'done' | 'error';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface WikiGenerateButtonProps {
  notebookId: string;
}

export default function WikiGenerateButton({ notebookId }: WikiGenerateButtonProps) {
  const router = useRouter();
  const [genState, setGenState] = useState<GenState>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [pagesDone, setPagesDone] = useState(0);
  const [pagesTotal, setPagesTotal] = useState(0);
  const [errorMsg, setErrorMsg] = useState('');

  // Poll job status while jobId is set. Clears on unmount.
  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const resp = await fetch(
          `${API_BASE}/notebooks/${notebookId}/wiki/jobs/${jobId}`,
        );
        if (!resp.ok) return; // transient error — retry on next tick
        const job = (await resp.json()) as {
          status: string;
          pages_done: number;
          pages_total: number;
          error?: string;
        };
        setPagesDone(job.pages_done ?? 0);
        setPagesTotal(job.pages_total ?? 0);
        if (job.status === 'completed') {
          setJobId(null);
          setGenState('done');
          router.refresh(); // re-fetches server component; wiki home redirects to first slug
        } else if (job.status === 'failed') {
          setJobId(null);
          setErrorMsg(job.error ?? 'Generation failed');
          setGenState('error');
        }
      } catch {
        // network hiccup — retry on next tick
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, notebookId, router]);

  async function handleGenerate() {
    setGenState('generating');
    setPagesDone(0);
    setPagesTotal(0);
    try {
      const resp = await fetch(
        `${API_BASE}/notebooks/${notebookId}/wiki/generate`,
        { method: 'POST' },
      );
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({})) as { detail?: string };
        setErrorMsg(err.detail ?? 'Generation failed');
        setGenState('error');
        return;
      }
      const data = (await resp.json()) as { job_id: string };
      setJobId(data.job_id); // triggers polling useEffect
    } catch {
      setErrorMsg('Network error — is the API running?');
      setGenState('error');
    }
  }

  if (genState === 'error') {
    return (
      <div className="flex flex-col items-center gap-3">
        <p className="text-destructive text-sm">{errorMsg}</p>
        <Button variant="outline" onClick={() => setGenState('idle')}>
          Try again
        </Button>
      </div>
    );
  }

  if (genState === 'generating' || genState === 'done') {
    const pct =
      pagesTotal > 0 ? Math.round((pagesDone / pagesTotal) * 100) : 0;
    return (
      <div className="flex flex-col items-center gap-3 w-64">
        <p className="text-sm text-muted-foreground">
          {genState === 'done'
            ? 'Wiki ready!'
            : `Generating… ${pagesDone} / ${pagesTotal || '?'} pages`}
        </p>
        <Progress value={genState === 'done' ? 100 : pct} className="w-full" />
      </div>
    );
  }

  return <Button onClick={handleGenerate}>Generate Wiki</Button>;
}
