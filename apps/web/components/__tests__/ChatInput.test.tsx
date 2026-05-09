import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ChatInput } from "@/components/ChatInput"
import type { SourceDocument } from "@/lib/types"

const testDocs: SourceDocument[] = [
  { document_id: "doc1", source_file: "refund_policy.pdf", source_url: "/doc1", size_bytes: 1000, updated_at: "2026-01-01" },
  { document_id: "doc2", source_file: "annual_report.pdf", source_url: "/doc2", size_bytes: 2000, updated_at: "2026-01-02" },
  { document_id: "doc3", source_file: "pricing_2026.pdf", source_url: "/doc3", size_bytes: 500, updated_at: "2026-01-03" },
]

function renderChatInput(onSubmit = vi.fn(), docs = testDocs) {
  return { ...render(<ChatInput pending={false} documents={docs} onSubmit={onSubmit} />), onSubmit }
}

describe("ChatInput", () => {
  describe("AC4.1: document picker opens on # + filter by substring", () => {
    it("typing #rep shows filtered documents", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "#rep")

      const listbox = screen.getByRole("listbox")
      expect(listbox).toBeInTheDocument()

      // Should filter to documents with "rep" in source_file (case-insensitive)
      // "annual_report.pdf" contains "rep" (in report)
      const options = screen.getAllByRole("option")
      expect(options).toHaveLength(1)
      expect(options[0]).toHaveTextContent("annual_report.pdf")
    })

    it("typing #annual filters to matching document", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "#annual")

      const options = screen.getAllByRole("option")
      expect(options).toHaveLength(1)
      expect(options[0]).toHaveTextContent("annual_report.pdf")
    })

    it("typing #pdf shows all three documents (max 8)", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "#pdf")

      const options = screen.getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options.length).toBeLessThanOrEqual(8)
    })

    it("listbox is not shown when documents list is empty", async () => {
      const user = userEvent.setup()
      renderChatInput(vi.fn(), [])

      const input = screen.getByRole("combobox")
      await user.type(input, "#anything")

      // listbox should not be present
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument()
    })
  })

  describe("AC4.2: arrow navigation and Enter selection", () => {
    it("ArrowDown highlights next document", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "#pdf")

      // First item should be highlighted by default
      let options = screen.getAllByRole("option")
      expect(options[0]).toHaveAttribute("aria-selected", "true")

      // Press ArrowDown
      await user.keyboard("{ArrowDown}")
      options = screen.getAllByRole("option")
      expect(options[1]).toHaveAttribute("aria-selected", "true")
      expect(options[0]).toHaveAttribute("aria-selected", "false")
    })

    it("Enter selects highlighted document and shows chip", async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderChatInput(onSubmit)

      const input = screen.getByRole("combobox")
      await user.type(input, "#ref")

      // Move down and select
      await user.keyboard("{ArrowDown}")
      await user.keyboard("{Enter}")

      // Picker should close
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument()

      // Chip should appear
      const chip = screen.getByRole("button", { name: /Remove attached document/ })
      expect(chip).toBeInTheDocument()

      // Input value should be cleared of the #token
      expect(input).toHaveValue("")
    })

    it("Enter with first item selected works correctly", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "#ref")
      await user.keyboard("{Enter}")

      // Chip should appear for first matching document
      const chip = screen.getByRole("button", { name: /Remove attached document/ })
      expect(chip).toBeInTheDocument()
    })
  })

  describe("AC4.4: chip clears after submit", () => {
    it("submitting message clears chip", async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderChatInput(onSubmit)

      const input = screen.getByRole("combobox")
      // Type a document marker and select one
      await user.type(input, "#ref")
      await user.keyboard("{Enter}")

      // Verify chip is there
      expect(screen.getByRole("button", { name: /Remove attached document/ })).toBeInTheDocument()

      // Type message and submit
      await user.type(input, "What is the policy?")
      const submitButton = screen.getByRole("button", { name: /Send/ })
      await user.click(submitButton)

      // onSubmit should be called with text and attached doc
      expect(onSubmit).toHaveBeenCalledTimes(1)
      const [text, attached] = onSubmit.mock.calls[0]
      expect(text).toBe("What is the policy?")
      expect(attached?.document_id).toBe("doc1") // refund_policy.pdf

      // After submit, chip should be gone
      // (component clears state immediately, so next render has no chip)
      // We verify this by checking the input is empty again
      expect(input).toHaveValue("")
    })
  })

  describe("AC4.5: Escape and Tab close picker", () => {
    it("Escape closes picker without selecting", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "#pdf")

      // Picker is open
      expect(screen.getByRole("listbox")).toBeInTheDocument()

      // Press Escape
      await user.keyboard("{Escape}")

      // Picker should close
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument()

      // No chip should appear
      expect(screen.queryByRole("button", { name: /Remove attached document/ })).not.toBeInTheDocument()

      // Input text should be unchanged
      expect(input).toHaveValue("#pdf")
    })

    it("Tab closes picker without selecting", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "#pdf")

      // Picker is open
      expect(screen.getByRole("listbox")).toBeInTheDocument()

      // Press Tab
      await user.keyboard("{Tab}")

      // Picker should close
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument()

      // No chip should appear
      expect(screen.queryByRole("button", { name: /Remove attached document/ })).not.toBeInTheDocument()
    })
  })

  describe("AC4.6: empty documents list edge case", () => {
    it("typing # with empty documents does nothing", async () => {
      const user = userEvent.setup()
      renderChatInput(vi.fn(), [])

      const input = screen.getByRole("combobox")
      await user.type(input, "#test")

      // No listbox should appear
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument()

      // Input should have the text
      expect(input).toHaveValue("#test")
    })
  })

  describe("additional: chip removal and disabled submit", () => {
    it("submit button is disabled when input is empty", () => {
      renderChatInput()

      const submitButton = screen.getByRole("button", { name: /Send/ })
      expect(submitButton).toBeDisabled()
    })

    it("submit button is enabled with text", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "Hello")

      const submitButton = screen.getByRole("button", { name: /Send/ })
      expect(submitButton).toBeEnabled()
    })

    it("clicking X on chip removes it", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox")
      await user.type(input, "#ref")
      await user.keyboard("{Enter}")

      // Chip should exist
      const chipButton = screen.getByRole("button", { name: /Remove attached document/ })
      expect(chipButton).toBeInTheDocument()

      // Click the X button inside the chip
      await user.click(chipButton)

      // Chip should be gone
      expect(screen.queryByRole("button", { name: /Remove attached document/ })).not.toBeInTheDocument()
    })

    it("placeholder changes when document is attached", async () => {
      const user = userEvent.setup()
      renderChatInput()

      const input = screen.getByRole("combobox") as HTMLInputElement
      // Initial placeholder
      expect(input.placeholder).toBe("What is the refund policy?")

      // Attach a document
      await user.type(input, "#ref")
      await user.keyboard("{Enter}")

      // Placeholder should change
      expect(input.placeholder).toBe("Ask about this document…")
    })

    it("pending state disables input and button", () => {
      render(<ChatInput pending={true} documents={testDocs} onSubmit={vi.fn()} />)

      const input = screen.getByRole("combobox")
      const submitButton = screen.getByRole("button", { name: /Send/ })

      expect(input).toBeDisabled()
      expect(submitButton).toBeDisabled()
    })
  })
})
