import { describe, it, expect, beforeEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { useQueryMode } from "@/lib/useQueryMode"

beforeEach(() => localStorage.clear())

describe("useQueryMode", () => {
  it("defaults to documents", () => {
    const { result } = renderHook(() => useQueryMode())
    expect(result.current[0]).toBe("documents")
  })

  it("persists general mode to localStorage", () => {
    const { result } = renderHook(() => useQueryMode())
    act(() => result.current[1]("general"))
    expect(localStorage.getItem("docquery.queryMode")).toBe("general")
  })

  it("hydrates from localStorage on mount", async () => {
    localStorage.setItem("docquery.queryMode", "general")
    const { result } = renderHook(() => useQueryMode())
    // useEffect fires after render; wait for hydration
    await waitFor(() => {
      expect(result.current[0]).toBe("general")
    })
  })
})
