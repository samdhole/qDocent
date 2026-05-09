// pattern: Imperative Shell
"use client"

import * as React from "react"
import type { Citation, RetrievedContext, SelectedCitation } from "@/lib/types"

type CitationContextValue = {
  citations: Citation[]
  retrievedContexts: RetrievedContext[]
  onSelectCitation?: (sel: SelectedCitation) => void
}

const CitationContext = React.createContext<CitationContextValue>({
  citations: [],
  retrievedContexts: [],
})

export function CitationProvider({
  citations,
  retrievedContexts,
  onSelectCitation,
  children,
}: CitationContextValue & { children: React.ReactNode }) {
  const value = React.useMemo(
    () => ({ citations, retrievedContexts, onSelectCitation }),
    [citations, retrievedContexts, onSelectCitation]
  )
  return (
    <CitationContext.Provider value={value}>
      {children}
    </CitationContext.Provider>
  )
}

export function useCitationContext() {
  return React.useContext(CitationContext)
}
