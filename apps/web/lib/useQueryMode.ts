// pattern: Imperative Shell
"use client"

import { useState, useEffect } from "react"

export type QueryMode = "documents" | "general"

const STORAGE_KEY = "docquery.queryMode"
const DEFAULT_MODE: QueryMode = "documents"

export function useQueryMode(): [QueryMode, (m: QueryMode) => void] {
  const [mode, setModeState] = useState<QueryMode>(DEFAULT_MODE)

  // SSR-safe hydration from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as QueryMode | null
      if (stored === "documents" || stored === "general") {
        setModeState(stored)
      }
    } catch {
      // localStorage unavailable (SSR, private mode) — use default
    }
  }, [])

  const setMode = (m: QueryMode) => {
    try {
      localStorage.setItem(STORAGE_KEY, m)
    } catch {
      // Ignore write failure
    }
    setModeState(m)
  }

  return [mode, setMode]
}
