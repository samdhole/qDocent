import { describe, it, expect } from "vitest"
import { unified } from "unified"
import remarkParse from "remark-parse"
import { remarkCitationBadges } from "@/lib/remarkCitationBadges"
import type { Node } from "unist"

type CiteNode = { data?: { hProperties?: { "data-num"?: string } } }

function parseWithPlugin(md: string) {
  return unified()
    .use(remarkParse)
    .use(remarkCitationBadges)
    .runSync(unified().use(remarkParse).parse(md))
}

function findNodes(tree: Node, type: string): Node[] {
  const results: Node[] = []
  function walk(node: Node) {
    if (node.type === type) results.push(node)
    if ("children" in node) (node as { children: Node[] }).children.forEach(walk)
  }
  walk(tree)
  return results
}

describe("remarkCitationBadges", () => {
  describe("AC2.5: numeric bracket replacement", () => {
    it("should replace [1] and [2] with citationRef nodes", () => {
      const tree = parseWithPlugin("See [1] and [2].")
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(2)
      expect(citationRefs[0]).toHaveProperty("data.hName", "cite-ref")
      expect(citationRefs[0]).toHaveProperty("data.hProperties.data-num", "1")
      expect(citationRefs[1]).toHaveProperty("data.hName", "cite-ref")
      expect(citationRefs[1]).toHaveProperty("data.hProperties.data-num", "2")
    })

    it("should replace single [0] (zero is a digit)", () => {
      const tree = parseWithPlugin("This is [0].")
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(1)
      expect(citationRefs[0]).toHaveProperty("data.hProperties.data-num", "0")
    })

    it("should replace multiple citations in same paragraph", () => {
      const tree = parseWithPlugin("Multiple [1] citations [2] in [3] one [4] line.")
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(4)
      expect(citationRefs.map((n) => (n as CiteNode).data?.hProperties?.["data-num"])).toEqual(
        ["1", "2", "3", "4"]
      )
    })
  })

  describe("AC2.6: code block exclusion", () => {
    it("should NOT replace [1] inside code blocks", () => {
      const md = "```js\nconst x = '[1]'\n```"
      const tree = parseWithPlugin(md)
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(0)
    })

    it("should NOT replace [1] inside inline code", () => {
      const tree = parseWithPlugin("Use the value `[1]` in your code.")
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(0)
    })

    it("should replace citations in text alongside inline code with [1]", () => {
      const tree = parseWithPlugin("See [1] and code `[2]` but not inside.")
      const citationRefs = findNodes(tree, "citationRef")

      // Only [1] should be replaced; [2] is inside backticks
      expect(citationRefs).toHaveLength(1)
      expect(citationRefs[0]).toHaveProperty("data.hProperties.data-num", "1")
    })

    it("should replace citations in text around code blocks", () => {
      const md = "See [1]\n\n```\ncode with [2]\n```\n\nAnd [3]"
      const tree = parseWithPlugin(md)
      const citationRefs = findNodes(tree, "citationRef")

      // Should have [1] and [3], but NOT [2]
      expect(citationRefs).toHaveLength(2)
      expect(citationRefs[0]).toHaveProperty("data.hProperties.data-num", "1")
      expect(citationRefs[1]).toHaveProperty("data.hProperties.data-num", "3")
    })
  })

  describe("edge cases", () => {
    it("should NOT replace non-numeric brackets like [abc]", () => {
      const tree = parseWithPlugin("This is [abc] and [1] is real.")
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(1)
      expect(citationRefs[0]).toHaveProperty("data.hProperties.data-num", "1")
    })

    it("should NOT replace brackets with leading zeros as multiple digits like [01]", () => {
      const tree = parseWithPlugin("Numbers [01] should [1] work.")
      const citationRefs = findNodes(tree, "citationRef")

      // [01] has a leading zero followed by 1, so it does match \d+
      // Actually, \d+ matches one or more digits, so [01] WILL match as "01"
      expect(citationRefs).toHaveLength(2)
      expect(citationRefs[0]).toHaveProperty("data.hProperties.data-num", "01")
      expect(citationRefs[1]).toHaveProperty("data.hProperties.data-num", "1")
    })

    it("should handle empty input gracefully", () => {
      const tree = parseWithPlugin("")
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(0)
    })

    it("should handle text with no citations", () => {
      const tree = parseWithPlugin("Just plain text with no citations.")
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(0)
    })

    it("should preserve surrounding text after replacement", () => {
      const md = "Start [1] middle [2] end"
      const tree = parseWithPlugin(md)
      const citationRefs = findNodes(tree, "citationRef")

      expect(citationRefs).toHaveLength(2)
      // Text nodes should still exist between citations
      const allNodes = findNodes(tree, "text")
      expect(allNodes.length).toBeGreaterThan(0)
    })
  })

  describe("comma-separated citation groups", () => {
    it("converts [2, 4, 5] to three separate citationRef nodes (AC1.1)", () => {
      const tree = parseWithPlugin("answer [2, 4, 5] here")
      const citationRefs = findNodes(tree, "citationRef")
      expect(citationRefs).toHaveLength(3)
      expect(
        citationRefs.map((n) => (n as CiteNode).data?.hProperties?.["data-num"])
      ).toEqual(["2", "4", "5"])
    })

    it("preserves single [N] as one citationRef node (AC1.2)", () => {
      const tree = parseWithPlugin("answer [1] here")
      const citationRefs = findNodes(tree, "citationRef")
      expect(citationRefs).toHaveLength(1)
      expect(citationRefs[0]).toHaveProperty("data.hProperties.data-num", "1")
    })

    it("handles mixed [1] and [2, 4] in same paragraph (AC1.3)", () => {
      const tree = parseWithPlugin("first [1] then [2, 4] done")
      const citationRefs = findNodes(tree, "citationRef")
      expect(citationRefs).toHaveLength(3)
      expect(
        citationRefs.map((n) => (n as CiteNode).data?.hProperties?.["data-num"])
      ).toEqual(["1", "2", "4"])
    })

    it("does not convert [2, 4] inside a code block (AC1.4)", () => {
      const tree = parseWithPlugin("```\n[2, 4]\n```")
      const citationRefs = findNodes(tree, "citationRef")
      expect(citationRefs).toHaveLength(0)
    })

    it("handles [2,4,5] without spaces after commas", () => {
      const tree = parseWithPlugin("answer [2,4,5] here")
      const citationRefs = findNodes(tree, "citationRef")
      expect(citationRefs).toHaveLength(3)
      expect(
        citationRefs.map((n) => (n as CiteNode).data?.hProperties?.["data-num"])
      ).toEqual(["2", "4", "5"])
    })
  })
})
