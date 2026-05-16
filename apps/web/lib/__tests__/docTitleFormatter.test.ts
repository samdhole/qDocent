import { describe, it, expect } from "vitest"
import { formatDocTitle } from "@/lib/docTitleFormatter"

describe("formatDocTitle", () => {
  it("strips file extension (AC6.1)", () => {
    expect(formatDocTitle("robinhood_10k_2024.pdf")).toBe("robinhood 10k 2024")
  })

  it("normalizes underscores to spaces (AC6.1)", () => {
    expect(formatDocTitle("annual_report_2023.pdf")).toBe("annual report 2023")
  })

  it("normalizes dashes to spaces (AC6.1)", () => {
    expect(formatDocTitle("q4-earnings-release.pdf")).toBe("q4 earnings release")
  })

  it("collapses multiple separators (AC6.1)", () => {
    expect(formatDocTitle("doc__with---mixed__separators.pdf")).toBe("doc with mixed separators")
  })

  it("truncates to 40 chars with ellipsis (AC6.2)", () => {
    const result = formatDocTitle("a-very-long-filename-that-exceeds-40-chars.pdf")
    expect(result.length).toBeLessThanOrEqual(41) // 40 chars + "…"
    expect(result.endsWith("…")).toBe(true)
    expect(result).not.toMatch(/ …$/)
  })

  it("does not truncate short titles (AC6.1)", () => {
    expect(formatDocTitle("report.pdf")).toBe("report")
  })

  it("handles filename that is exactly 40 chars after normalization", () => {
    // 40 character string (no truncation expected)
    const input = "a".repeat(40) + ".pdf"
    const result = formatDocTitle(input)
    expect(result).toBe("a".repeat(40))
    expect(result.endsWith("…")).toBe(false)
  })

  it("trims leading/trailing separators (AC6.1 defensive)", () => {
    expect(formatDocTitle("_doc_.pdf")).toBe("doc")
  })

  it("handles filename with no extension", () => {
    expect(formatDocTitle("my_document")).toBe("my document")
  })

  it("handles empty string", () => {
    expect(formatDocTitle("")).toBe("")
  })
})
