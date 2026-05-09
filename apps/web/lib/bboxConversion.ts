// pattern: Functional Core
// Convert pdfplumber/PyMuPDF bbox coordinates to react-pdf's CSS-pixel space.
// pdfplumber: [x0, top, x1, bottom] in PDF points (1/72 inch), origin at top-left.
// react-pdf renders the page at a fixed pixel width; we scale by the rendered page's
// width / the PDF page's natural width (in points) — both available at render time.

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
