import { describe, it, expect } from "vitest";
import { bboxToCssBox } from "@/lib/bboxConversion";

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
