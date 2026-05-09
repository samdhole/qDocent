import type { Citation, SelectedCitation } from "./types";

export function canOpenSource(
  citation: Citation | null | undefined,
  onSelectCitation: ((sel: SelectedCitation) => void) | undefined
): boolean {
  return Boolean(
    citation && citation.document_id && citation.page != null && onSelectCitation
  );
}
