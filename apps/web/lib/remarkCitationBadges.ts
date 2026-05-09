// pattern: Functional Core
import { findAndReplace } from "mdast-util-find-and-replace"
import type { PhrasingContent, Root } from "mdast"

const CITATION_RE = /\[(\d+)\]/g

export function remarkCitationBadges() {
  return (tree: Root) => {
    findAndReplace(
      tree,
      [
        [
          CITATION_RE,
          (_match: string, num: string) => {
            // mdast-util-find-and-replace expects a node assignable to mdast
            // `PhrasingContent`. The custom `citationRef` type is not in that
            // union, but it is forwarded as a hast element via data.hName +
            // data.hProperties at the rehype step. The double cast is the
            // standard escape hatch for ecosystem-extension nodes.
            return {
              type: "citationRef",
              data: {
                hName: "cite-ref",
                hProperties: { "data-num": num },
              },
            } as unknown as PhrasingContent
          },
        ],
      ],
      { ignore: ["code", "inlineCode"] }
    )
  }
}
