// pattern: Functional Core (no I/O — pure presentation)
import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

type Props = {
  icon: LucideIcon;
  title: string;
  body: string;
  action?: React.ReactNode;
};

export function EmptyState({ icon: Icon, title, body, action }: Props) {
  return (
    <Card>
      <CardContent className="py-12 flex flex-col items-center text-center gap-3">
        <div className="size-12 rounded-full bg-muted flex items-center justify-center">
          <Icon className="size-6 text-muted-foreground" />
        </div>
        <div className="space-y-1">
          <p className="font-medium">{title}</p>
          <p className="text-sm text-muted-foreground max-w-sm">{body}</p>
        </div>
        {action}
      </CardContent>
    </Card>
  );
}
