// pattern: Imperative Shell
"use client"

import type { QueryMode } from "@/lib/useQueryMode"
import { cn } from "@/lib/utils"

type Props = {
  mode: QueryMode
  onChange: (m: QueryMode) => void
}

export function QueryModeToggle({ mode, onChange }: Props) {
  return (
    <div
      className="flex rounded-md border border-input bg-background text-xs"
      role="group"
      aria-label="Query mode"
    >
      <button
        type="button"
        onClick={() => onChange("documents")}
        className={cn(
          "px-2.5 py-1 rounded-l-md transition-colors",
          mode === "documents"
            ? "bg-primary text-primary-foreground font-medium"
            : "text-muted-foreground hover:bg-muted"
        )}
        title="Answer only from your ingested documents"
        aria-pressed={mode === "documents"}
      >
        Docs
      </button>
      <button
        type="button"
        onClick={() => onChange("general")}
        className={cn(
          "px-2.5 py-1 rounded-r-md transition-colors",
          mode === "general"
            ? "bg-primary text-primary-foreground font-medium"
            : "text-muted-foreground hover:bg-muted"
        )}
        title="Answer from documents and general knowledge"
        aria-pressed={mode === "general"}
      >
        General
      </button>
    </div>
  )
}
