import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { CitationProvider } from "@/components/CitationContext"
import { CitationBadge } from "@/components/CitationBadge"
import type { Citation } from "@/lib/types"

const testCitations = [
  { document: "policy.pdf", document_id: "doc1", page: 3, page_end: 5, chunk_id: "abc", chunk_index: 1 },
  { document: "report.pdf", document_id: "doc2", page: 7, page_end: 9, chunk_id: "def", chunk_index: 2 },
]
const testContexts = [
  { chunk_id: "abc", text: "The refund policy states 30 days.", score: 0.85 },
  { chunk_id: "def", text: "Annual report summary.", score: 0.72 },
]

function renderBadge(index: number, onSelectCitation = vi.fn()) {
  render(
    <CitationProvider citations={testCitations} retrievedContexts={testContexts} onSelectCitation={onSelectCitation}>
      <CitationBadge index={index} />
    </CitationProvider>
  )
  return { onSelectCitation }
}

describe("CitationBadge", () => {
  it("AC1.3: click invokes onSelectCitation with correct payload", async () => {
    const onSelectCitation = vi.fn()
    const user = userEvent.setup()

    render(
      <CitationProvider citations={testCitations} retrievedContexts={testContexts} onSelectCitation={onSelectCitation}>
        <CitationBadge index={1} />
      </CitationProvider>
    )

    const button = screen.getByRole("button", { name: /Citation 1/ })
    await user.click(button)

    expect(onSelectCitation).toHaveBeenCalledTimes(1)
    expect(onSelectCitation).toHaveBeenCalledWith({
      documentId: "doc1",
      documentName: "policy.pdf",
      pageStart: 3,
      pageEnd: 5,
      chunkIndex: 1,
    })
  })

  it("AC1.3: Enter key invokes onSelectCitation", async () => {
    const onSelectCitation = vi.fn()
    const user = userEvent.setup()

    render(
      <CitationProvider citations={testCitations} retrievedContexts={testContexts} onSelectCitation={onSelectCitation}>
        <CitationBadge index={2} />
      </CitationProvider>
    )

    const button = screen.getByRole("button", { name: /Citation 2/ })
    button.focus()
    await user.keyboard("{Enter}")

    expect(onSelectCitation).toHaveBeenCalledTimes(1)
    expect(onSelectCitation).toHaveBeenCalledWith({
      documentId: "doc2",
      documentName: "report.pdf",
      pageStart: 7,
      pageEnd: 9,
      chunkIndex: 2,
    })
  })

  it("AC1.3: Space key invokes onSelectCitation", async () => {
    const onSelectCitation = vi.fn()
    const user = userEvent.setup()
    const citationsForSpace: typeof testCitations = [
      { document: "policy.pdf", document_id: "doc1", page: 3, page_end: 5, chunk_id: "abc", chunk_index: 1 },
    ]

    render(
      <CitationProvider citations={citationsForSpace} retrievedContexts={testContexts} onSelectCitation={onSelectCitation}>
        <CitationBadge index={1} />
      </CitationProvider>
    )

    const button = screen.getByRole("button", { name: /Citation 1/ })
    button.focus()
    await user.keyboard(" ")

    expect(onSelectCitation).toHaveBeenCalledTimes(1)
    expect(onSelectCitation).toHaveBeenCalledWith({
      documentId: "doc1",
      documentName: "policy.pdf",
      pageStart: 3,
      pageEnd: 5,
      chunkIndex: 1,
    })
  })

  it("AC1.4: out-of-bounds index renders greyed fallback", () => {
    const { onSelectCitation } = renderBadge(99)

    const badge = screen.getByText("[99]")
    expect(badge).toBeInTheDocument()
    // Should be a span, not a button
    expect(badge.tagName).toBe("SPAN")
    expect(onSelectCitation).not.toHaveBeenCalled()
  })

  it("AC1.4: out-of-bounds fallback does not invoke onSelectCitation on click", async () => {
    const onSelectCitation = vi.fn()
    const user = userEvent.setup()

    render(
      <CitationProvider citations={testCitations} retrievedContexts={testContexts} onSelectCitation={onSelectCitation}>
        <CitationBadge index={99} />
      </CitationProvider>
    )

    const badge = screen.getByText("[99]")
    await user.click(badge)

    expect(onSelectCitation).not.toHaveBeenCalled()
  })

  it("guard: missing document_id renders disabled button, no onSelectCitation call", async () => {
    const onSelectCitation = vi.fn()
    const user = userEvent.setup()
    const citationsWithoutDocId = [
      { document: "policy.pdf", document_id: undefined, page: 3, page_end: 5, chunk_id: "abc", chunk_index: 1 },
    ]

    render(
      <CitationProvider citations={citationsWithoutDocId} retrievedContexts={testContexts} onSelectCitation={onSelectCitation}>
        <CitationBadge index={1} />
      </CitationProvider>
    )

    const button = screen.getByRole("button")
    expect(button).toBeDisabled()

    await user.click(button)
    expect(onSelectCitation).not.toHaveBeenCalled()
  })

  it("guard: missing page renders disabled button, no onSelectCitation call", async () => {
    const onSelectCitation = vi.fn()
    const user = userEvent.setup()
    const citationsWithoutPage = [
      { document: "policy.pdf", document_id: "doc1", page: undefined, page_end: 5, chunk_id: "abc", chunk_index: 1 },
    ]

    render(
      <CitationProvider citations={citationsWithoutPage} retrievedContexts={testContexts} onSelectCitation={onSelectCitation}>
        <CitationBadge index={1} />
      </CitationProvider>
    )

    const button = screen.getByRole("button")
    expect(button).toBeDisabled()

    await user.click(button)
    expect(onSelectCitation).not.toHaveBeenCalled()
  })

  it("pageEnd and chunkIndex default to null when undefined", async () => {
    const onSelectCitation = vi.fn()
    const user = userEvent.setup()
    const citationsWithoutOptionals: Citation[] = [
      { document: "policy.pdf", document_id: "doc1", page: 3, chunk_id: "abc" },
    ]

    render(
      <CitationProvider citations={citationsWithoutOptionals} retrievedContexts={testContexts} onSelectCitation={onSelectCitation}>
        <CitationBadge index={1} />
      </CitationProvider>
    )

    const button = screen.getByRole("button")
    await user.click(button)

    expect(onSelectCitation).toHaveBeenCalledWith({
      documentId: "doc1",
      documentName: "policy.pdf",
      pageStart: 3,
      pageEnd: null,
      chunkIndex: null,
    })
  })
})
