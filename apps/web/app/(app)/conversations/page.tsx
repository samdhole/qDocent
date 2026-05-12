'use client';

import { useEffect, useState } from 'react';
import ConversationList from '@/components/ConversationList';
import type { ConversationRecord } from '@/components/ConversationItem';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface Notebook {
  id: string;
  name: string;
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [filterNotebookId, setFilterNotebookId] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const url = filterNotebookId
          ? `${API_BASE}/conversations?notebook_id=${filterNotebookId}`
          : `${API_BASE}/conversations`;
        const [convResp, nbResp] = await Promise.all([
          fetch(url),
          fetch(`${API_BASE}/notebooks`),
        ]);
        if (convResp.ok) setConversations(await convResp.json());
        if (nbResp.ok) setNotebooks(await nbResp.json());
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [filterNotebookId]);

  const notebookMap = Object.fromEntries(notebooks.map((nb) => [nb.id, nb.name]));

  return (
    <div className="p-6 space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Conversations</h1>
        <select
          value={filterNotebookId}
          onChange={(e) => setFilterNotebookId(e.target.value)}
          className="border border-input rounded-md px-3 py-1.5 text-sm bg-background text-foreground"
        >
          <option value="">All notebooks</option>
          {notebooks.map((nb) => (
            <option key={nb.id} value={nb.id}>
              {nb.name}
            </option>
          ))}
        </select>
      </div>
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <ConversationList conversations={conversations} notebookMap={notebookMap} />
      )}
    </div>
  );
}
