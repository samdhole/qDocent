// pattern: Functional Core
// Convert pdfplumber/PyMuPDF bbox coordinates to react-pdf's CSS-pixel space.
// pdfplumber: [x0, top, x1, bottom] in PDF points (1/72 inch), origin at top-left.
// react-pdf renders the page at a fixed pixel width; we scale by the rendered page's
// width / the PDF page's natural width (in points) — both available at render time.

import type { ChunkManifestEntry, SelectedCitation } from "@/lib/types";

export type BBox = [number, number, number, number];

export type RenderedPageDimensions = {
  pageWidthPx: number; // rendered width in CSS pixels
  pageHeightPx: number; // rendered height in CSS pixels
  naturalWidthPt: number; // PDF intrinsic width in points
  naturalHeightPt: number; // PDF intrinsic height in points
};

export type CssBox = { left: number; top: number; width: number; height: number };

export function bboxToCssBox(bbox: BBox, dims: RenderedPageDimensions): CssBox {
  const [x0, top, x1, bottom] = bbox;
  const scaleX = dims.pageWidthPx / dims.naturalWidthPt;
  const scaleY = dims.pageHeightPx / dims.naturalHeightPt;
  return {
    left: x0 * scaleX,
    top: top * scaleY,
    width: (x1 - x0) * scaleX,
    height: (bottom - top) * scaleY,
  };
}

export function findOverlayChunk(
  chunks: ChunkManifestEntry[],
  citation: SelectedCitation | null,
  pageNum: number | null,
): ChunkManifestEntry | null {
  if (!citation || pageNum == null || chunks.length === 0) return null;
  if (citation.chunkIndex != null) {
    const exact = chunks.find((c) => c.chunk_index === citation.chunkIndex);
    if (
      exact &&
      (exact.page_start ?? 0) <= pageNum &&
      pageNum <= (exact.page_end ?? exact.page_start ?? 0)
    ) {
      return exact;
    }
  }
  return (
    chunks.find(
      (c) =>
        c.bbox != null &&
        (c.page_start ?? 0) <= pageNum &&
        pageNum <= (c.page_end ?? c.page_start ?? 0),
    ) ?? null
  );
}

// A bbox that covers ≥90% of both page dimensions is treated as "full page" —
// the ingestion pipeline emits these for text chunks that span the body column.
// Rendering a full-page overlay would obscure the content rather than highlight it.
export function isFullPageBbox(
  bbox: BBox,
  naturalWidthPt: number,
  naturalHeightPt: number,
): boolean {
  const [x0, top, x1, bottom] = bbox;
  const widthRatio = (x1 - x0) / naturalWidthPt;
  const heightRatio = (bottom - top) / naturalHeightPt;
  return widthRatio >= 0.9 && heightRatio >= 0.9;
}
