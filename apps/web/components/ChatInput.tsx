// pattern: Imperative Shell
"use client"

import * as React from "react"
import { ArrowUp, FileText, Loader2, X } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { SourceDocument } from "@/lib/types"

type Props = {
  pending: boolean
  documents: SourceDocument[]
  onSubmit: (text: string, attached?: SourceDocument[]) => void
}

export function ChatInput({ pending, documents, onSubmit }: Props) {
  const [text, setText] = React.useState("")
  const [attachedDocs, setAttachedDocs] = React.useState<SourceDocument[]>([])
  const [pickerOpen, setPickerOpen] = React.useState(false)
  const [pickerQuery, setPickerQuery] = React.useState("")
  const [highlightIndex, setHighlightIndex] = React.useState(0)

  const inputRef = React.useRef<HTMLInputElement>(null)
  const listboxId = "doc-picker-listbox"

  // Filter documents by picker query (case-insensitive substring, max 8)
  const filtered = React.useMemo(
    () =>
      pickerQuery
        ? documents
            .filter((d) => !attachedDocs.some((a) => a.document_id === d.document_id))
            .filter((d) =>
              d.source_file.toLowerCase().includes(pickerQuery.toLowerCase())
            )
            .slice(0, 8)
        : documents
            .filter((d) => !attachedDocs.some((a) => a.document_id === d.document_id))
            .slice(0, 8),
    [attachedDocs, documents, pickerQuery]
  )

  // Extract # token from text up to caret
  function getHashToken(value: string, caret: number): { token: string; start: number } | null {
    const before = value.slice(0, caret)
    const match = before.match(/#(\S*)$/)
    if (!match) return null
    return { token: match[1], start: before.length - match[0].length }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value
    setText(value)
    const caret = e.target.selectionStart ?? value.length
    const hashToken = getHashToken(value, caret)

    // Bare # (empty token) is intentional — opens the full list for browsing
    // rather than requiring a character first. This improves UX by allowing users
    // to discover available documents immediately.
    if (hashToken !== null && documents.length > 0) {
      setPickerQuery(hashToken.token)
      setPickerOpen(true)
      setHighlightIndex(0)
    } else {
      setPickerOpen(false)
    }
  }

  function selectDoc(doc: SourceDocument) {
    // Remove the #token from text
    const caret = inputRef.current?.selectionStart ?? text.length
    const hashToken = getHashToken(text, caret)
    if (hashToken !== null) {
      setText(text.slice(0, hashToken.start) + text.slice(hashToken.start + hashToken.token.length + 1))
    }
    setAttachedDocs((prev) =>
      prev.some((d) => d.document_id === doc.document_id) ? prev : [...prev, doc]
    )
    setPickerOpen(false)
    setPickerQuery("")
    inputRef.current?.focus()
  }

  function removeDoc(documentId: string) {
    setAttachedDocs((prev) => prev.filter((d) => d.document_id !== documentId))
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!pickerOpen) return
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setHighlightIndex((i) => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setHighlightIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === "Enter") {
      e.preventDefault()
      if (filtered[highlightIndex]) selectDoc(filtered[highlightIndex])
    } else if (e.key === "Escape" || e.key === "Tab") {
      setPickerOpen(false)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    const attached = attachedDocs.length > 0 ? attachedDocs : undefined
    setText("")
    setAttachedDocs([])
    onSubmit(trimmed, attached)
  }

  const activeDescendant = pickerOpen && filtered[highlightIndex]
    ? `doc-option-${highlightIndex}`
    : undefined

  return (
    <form onSubmit={handleSubmit} className="relative flex flex-col gap-2 mt-4 pt-4 border-t">
      {attachedDocs.length > 0 && (
        <div className="flex flex-wrap gap-1 px-1 pt-1">
          {attachedDocs.map((doc) => (
            <Badge key={doc.document_id} variant="secondary" className="gap-1 text-xs">
              <FileText className="size-3" />
              <span className="max-w-[120px] truncate">{doc.source_file}</span>
              <button
                type="button"
                onClick={() => removeDoc(doc.document_id)}
                aria-label={`Remove ${doc.source_file}`}
                className="ml-1 rounded-full hover:bg-muted"
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Picker listbox */}
      {pickerOpen && filtered.length > 0 && (
        <ul
          id={listboxId}
          role="listbox"
          aria-label="Documents"
          className="absolute bottom-full mb-1 left-0 right-0 z-50 max-h-52 overflow-y-auto rounded-md border bg-popover shadow-md"
        >
          {filtered.map((doc, i) => (
            <li
              key={doc.document_id}
              id={`doc-option-${i}`}
              role="option"
              aria-selected={i === highlightIndex}
              onMouseDown={(e) => { e.preventDefault(); selectDoc(doc) }}
              className={cn(
                "cursor-pointer px-3 py-2 text-sm truncate",
                i === highlightIndex && "bg-accent text-accent-foreground"
              )}
            >
              {doc.source_file}
            </li>
          ))}
        </ul>
      )}

      {/* Input row */}
      <div className="flex gap-2">
        <Input
          ref={inputRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={attachedDocs.length > 0 ? "Ask about selected documents..." : "What is the refund policy?"}
          disabled={pending}
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={pickerOpen}
          aria-controls={pickerOpen ? listboxId : undefined}
          aria-activedescendant={activeDescendant}
          aria-autocomplete="list"
          className="flex-1"
        />
        <Button type="submit" disabled={pending || !text.trim()}>
          {pending ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
          <span className="sr-only">Send</span>
        </Button>
      </div>
    </form>
  )
}
