// pattern: Imperative Shell
"use client"

import * as React from "react"
import { HoverCard, HoverCardTrigger, HoverCardContent } from "@/components/ui/hover-card"
import { useCitationContext } from "@/components/CitationContext"
import { canOpenSource } from "@/lib/citationClickable"
import { cn } from "@/lib/utils"

type Props = {
  index: number          // 1-based, matches [N] in prose
  variant?: "inline" | "panel"
}

export function CitationBadge({ index, variant = "inline" }: Props) {
  const { citations, retrievedContexts, onSelectCitation } = useCitationContext()

  const citation = citations[index - 1]
  const context = retrievedContexts[index - 1]

  const isClickable = canOpenSource(citation, onSelectCitation)

  const handleSelect = () => {
    if (!citation || !isClickable || !onSelectCitation) return
    onSelectCitation({
      documentId: citation.document_id!,
      documentName: citation.document,
      pageStart: citation.page!,
      pageEnd: citation.page_end ?? null,
      chunkIndex: citation.chunk_index ?? null,
    })
  }

  // Out-of-bounds → greyed fallback with no interaction
  if (!citation) {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded px-1 text-xs text-muted-foreground bg-muted cursor-default",
          variant === "panel" && "px-2 py-0.5"
        )}
        aria-label={`Citation ${index} (unavailable)`}
      >
        [{index}]
      </span>
    )
  }

  const badgeClasses = cn(
    "inline-flex items-center rounded px-1 text-xs font-medium",
    isClickable
      ? "bg-blue-50 text-blue-700 hover:bg-blue-100 cursor-pointer"
      : "bg-muted text-muted-foreground cursor-default",
    variant === "panel" && "px-2 py-0.5 text-sm"
  )

  // Non-clickable badges: plain disabled button with no hover card (no source to open).
  if (!isClickable) {
    return (
      <button
        type="button"
        disabled
        className={badgeClasses}
        aria-label={`Citation ${index}: ${citation.document ?? "source"} (no source link)`}
      >
        [{index}]
      </button>
    )
  }

  // Clickable badges: HoverCard for touch-accessible chunk preview.
  // Hovering shows the chunk text preview; clicking opens the SourcePanel.
  return (
    <HoverCard openDelay={150} closeDelay={75}>
      {/* 150ms openDelay matches AC2.1 hover-open threshold */}
      <HoverCardTrigger asChild>
        <button
          type="button"
          onClick={handleSelect}
          className={badgeClasses}
          aria-label={`Citation ${index}: ${citation.document ?? "source"}`}
        >
          [{index}]
        </button>
      </HoverCardTrigger>
      <HoverCardContent side="top" align="start" className="w-72">
        <div className="space-y-1.5">
          {context?.text && (
            <p className="text-xs leading-relaxed line-clamp-4">{context.text}</p>
          )}
          <p className="text-xs text-muted-foreground">
            {[
              citation.page != null && `p.${citation.page}`,
              citation.document,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
      </HoverCardContent>
    </HoverCard>
  )
}
