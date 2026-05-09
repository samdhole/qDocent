// pattern: Imperative Shell
"use client"

import * as React from "react"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { useCitationContext } from "@/components/CitationContext"
import { cn } from "@/lib/utils"

type Props = {
  index: number          // 1-based, matches [N] in prose
  variant?: "inline" | "panel"
}

export function CitationBadge({ index, variant = "inline" }: Props) {
  const { citations, retrievedContexts, onSelectCitation } = useCitationContext()

  const citation = citations[index - 1]
  const context = retrievedContexts[index - 1]

  // Match the existing AnswerCard guard: only invoke onSelectCitation when
  // document_id is present AND page is present. Otherwise click is a no-op.
  const canOpenSource = Boolean(
    citation && citation.document_id && citation.page != null && onSelectCitation
  )

  const handleSelect = () => {
    if (!citation || !canOpenSource || !onSelectCitation) return
    onSelectCitation({
      documentId: citation.document_id!,
      documentName: citation.document,
      pageStart: citation.page!,
      pageEnd: citation.page_end ?? null,
      chunkIndex: citation.chunk_index ?? null,
    })
  }

  // AC1.4: out-of-bounds → greyed fallback with no hover
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

  const trigger = (
    <button
      type="button"
      onClick={handleSelect}
      onKeyDown={(e) => { if (e.key === "Enter") handleSelect() }}
      disabled={!canOpenSource}
      className={cn(
        "inline-flex items-center rounded px-1 text-xs font-medium",
        canOpenSource
          ? "bg-blue-50 text-blue-700 hover:bg-blue-100 cursor-pointer"
          : "bg-muted text-muted-foreground cursor-default",
        variant === "panel" && "px-2 py-0.5 text-sm"
      )}
      aria-label={`Citation ${index}: ${citation.document ?? "source"}`}
    >
      [{index}]
    </button>
  )

  const hoverContent = (
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
      {canOpenSource && (
        <button
          type="button"
          onClick={handleSelect}
          className="text-xs text-blue-600 hover:underline"
        >
          Open source →
        </button>
      )}
    </div>
  )

  return (
    // AC1.1: openDelay=150ms (~150ms per design spec; within the 200ms success criterion)
    <HoverCard openDelay={150} closeDelay={200}>
      <HoverCardTrigger asChild>{trigger}</HoverCardTrigger>
      {/* AC1.2: verbatim text, document name, page footer */}
      <HoverCardContent className="w-80" side="top" align="start">
        {hoverContent}
      </HoverCardContent>
    </HoverCard>
  )
}
