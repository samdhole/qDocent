// pattern: Functional Core
import ConversationItem, { ConversationRecord } from '@/components/ConversationItem';

interface ConversationListProps {
  conversations: ConversationRecord[];
  notebookMap: Record<string, string>;
}

export default function ConversationList({
  conversations,
  notebookMap,
}: ConversationListProps) {
  if (conversations.length === 0) {
    return (
      <p className="text-muted-foreground text-sm text-center py-12">
        No conversations yet.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {conversations.map((conv) => (
        <ConversationItem
          key={conv.r2r_conv_id}
          conversation={conv}
          notebookName={
            conv.notebook_id ? notebookMap[conv.notebook_id] : undefined
          }
        />
      ))}
    </div>
  );
}
