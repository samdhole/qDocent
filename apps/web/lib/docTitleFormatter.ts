// pattern: Functional Core

// Strips file extension, normalizes separators (underscore/dash → space),
// collapses whitespace, and truncates to 40 visible characters.
export function formatDocTitle(sourceFile: string): string {
  const withoutExt = sourceFile.replace(/\.[^.]+$/, "")
  const normalized = withoutExt.replace(/[_-]/g, " ").replace(/\s+/g, " ").trim()
  return normalized.length > 40 ? normalized.slice(0, 40).trimEnd() + "…" : normalized
}
