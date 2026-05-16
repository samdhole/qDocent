// pattern: Functional Core
import { findAndReplace } from "mdast-util-find-and-replace"
import type { PhrasingContent, Root } from "mdast"

// Matches [N] or [N, M, K, ...] — captures the inner content (digits + optional comma-space-digits).
const CITATION_RE = /\[(\d+(?:,\s*\d+)*)\]/g

export function remarkCitationBadges() {
  return (tree: Root) => {
    findAndReplace(
      tree,
      [
        [
          CITATION_RE,
          (_match: string, capture: string) => {
            const nums = capture.split(",").map((s) => s.trim()).filter((s) => /^\d+$/.test(s))
            // Defensive guard: regex guarantees at least one digit group, but
            // the filter is a safety net for unexpected capture shapes.
            if (nums.length === 0) return false
            return nums.map((num) => ({
              type: "citationRef",
              data: {
                hName: "cite-ref",
                hProperties: { "data-num": num },
              },
            } as unknown as PhrasingContent))
          },
        ],
      ],
      { ignore: ["code", "inlineCode"] }
    )
  }
}
