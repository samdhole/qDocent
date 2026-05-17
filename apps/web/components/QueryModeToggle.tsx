// pattern: Imperative Shell
"use client"

import type { QueryMode } from "@/lib/useQueryMode"
import { cn } from "@/lib/utils"

type Props = {
  mode: QueryMode
  onChange: (m: QueryMode) => void
}

const MODE_DESCRIPTION: Record<QueryMode, string> = {
  documents: "Answers from your ingested documents only",
  general: "Answers from documents + broad LLM knowledge",
}

export function QueryModeToggle({ mode, onChange }: Props) {
  return (
    <div className="flex flex-col items-end gap-1">
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
          aria-pressed={mode === "general"}
        >
          General
        </button>
      </div>
      <p className="text-[10px] text-muted-foreground">{MODE_DESCRIPTION[mode]}</p>
    </div>
  )
}
