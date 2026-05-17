// pattern: Functional Core
import Link from 'next/link';

export interface ConversationRecord {
  r2r_conv_id: string;
  notebook_id: string | null;
  title: string;
  created_at: string;
}

interface ConversationItemProps {
  conversation: ConversationRecord;
  notebookName?: string;
}

export default function ConversationItem({
  conversation,
  notebookName,
}: ConversationItemProps) {
  const href = conversation.notebook_id
    ? `/notebooks/${conversation.notebook_id}?resume=${conversation.r2r_conv_id}`
    : `/ask`;

  const date = new Date(conversation.created_at).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  return (
    <Link
      href={href}
      className="block p-4 border border-border rounded-lg hover:bg-accent/50 transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <p className="font-medium text-sm text-foreground line-clamp-1">
          {conversation.title}
        </p>
        <p className="text-xs text-muted-foreground shrink-0">{date}</p>
      </div>
      <p className="text-xs text-muted-foreground mt-1">
        {notebookName ?? (conversation.notebook_id ? conversation.notebook_id : 'No notebook')}
      </p>
    </Link>
  );
}
