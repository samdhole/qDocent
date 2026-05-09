"use client";

import { CheckCircle2, XCircle, Loader2, Clock, X } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";

import type { UploadItem } from "@/lib/useUploadQueue";

const STATUS_ICON = {
  queued: Clock,
  uploading: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
} as const;

const STATUS_COLOR = {
  queued: "text-muted-foreground",
  uploading: "text-primary animate-spin",
  completed: "text-green-700",
  failed: "text-destructive",
} as const;

type Props = {
  items: UploadItem[];
  onRemove: (id: string) => void;
};

export function UploadQueueList({ items, onRemove }: Props) {
  if (items.length === 0) return null;
  return (
    <Card>
      <CardContent className="pt-4 space-y-3">
        {items.map((item) => {
          const Icon = STATUS_ICON[item.status];
          return (
            <div key={item.id} className="flex items-center gap-3">
              <Icon className={`size-4 shrink-0 ${STATUS_COLOR[item.status]}`} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{item.file.name}</p>
                {item.error && <p className="text-xs text-destructive">{item.error}</p>}
                <Progress value={item.progress} className="h-1 mt-1" />
              </div>
              {(item.status === "completed" || item.status === "failed") && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  onClick={() => onRemove(item.id)}
                >
                  <X className="size-3" />
                  <span className="sr-only">Remove</span>
                </Button>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
