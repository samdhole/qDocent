import { describe, it, expect } from "vitest";
import { bboxToCssBox, findOverlayChunk } from "@/lib/bboxConversion";
import type { ChunkManifestEntry, SelectedCitation } from "@/lib/types";

describe("bboxToCssBox", () => {
  it("scales pdfplumber bbox to css pixels using rendered/natural width ratio", () => {
    // Page is 612pt x 792pt (US Letter); rendered at 612px wide (1:1 scale).
    const css = bboxToCssBox([100, 200, 300, 250], {
      pageWidthPx: 612,
      pageHeightPx: 792,
      naturalWidthPt: 612,
      naturalHeightPt: 792,
    });
    expect(css).toEqual({ left: 100, top: 200, width: 200, height: 50 });
  });

  it("scales bbox down when rendered width is half the natural width", () => {
    const css = bboxToCssBox([100, 200, 300, 250], {
      pageWidthPx: 306,
      pageHeightPx: 396,
      naturalWidthPt: 612,
      naturalHeightPt: 792,
    });
    expect(css).toEqual({ left: 50, top: 100, width: 100, height: 25 });
  });

  it("handles non-uniform x/y scale ratios", () => {
    const css = bboxToCssBox([0, 0, 100, 100], {
      pageWidthPx: 200,
      pageHeightPx: 50,
      naturalWidthPt: 100,
      naturalHeightPt: 100,
    });
    // x scale = 2, y scale = 0.5
    expect(css).toEqual({ left: 0, top: 0, width: 200, height: 50 });
  });
});

const baseCitation: SelectedCitation = {
  documentId: "doc1",
  documentName: "test.pdf",
  pageStart: 1,
  pageEnd: null,
  chunkIndex: null,
};

const chunk1: ChunkManifestEntry = {
  chunk_index: 0,
  page_start: 1,
  page_end: 1,
  bbox: [10, 20, 100, 50],
  section_path: null,
  text_preview: "hello",
};

describe("findOverlayChunk", () => {
  it("returns null when chunks is empty (AC7.5)", () => {
    expect(findOverlayChunk([], baseCitation, 1)).toBeNull();
  });

  it("returns null when citation is null", () => {
    expect(findOverlayChunk([chunk1], null, 1)).toBeNull();
  });

  it("returns null when pageNum is null", () => {
    expect(findOverlayChunk([chunk1], baseCitation, null)).toBeNull();
  });

  it("returns exact chunk when chunkIndex matches", () => {
    const citation: SelectedCitation = { ...baseCitation, chunkIndex: 0 };
    const result = findOverlayChunk([chunk1], citation, 1);
    expect(result?.chunk_index).toBe(0);
  });

  it("falls back to page-range match when chunkIndex is null", () => {
    const result = findOverlayChunk([chunk1], baseCitation, 1);
    expect(result?.chunk_index).toBe(0);
  });

  it("returns null when no chunk matches the page range", () => {
    const result = findOverlayChunk([chunk1], baseCitation, 99);
    expect(result).toBeNull();
  });
});
