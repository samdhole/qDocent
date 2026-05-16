import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SourcePanel from "../SourcePanel";
import type { ChunksResponse, SelectedCitation, ChunkManifestEntry } from "@/lib/types";

// Mock props types for Document and Page components
type DocumentMockProps = {
  children: React.ReactNode;
  file?: string;
  loading?: React.ReactNode;
  error?: React.ReactNode;
};

type PageMockProps = {
  children?: React.ReactNode;
  pageNumber: number;
};

type BboxDims = {
  pageWidthPx?: number;
  pageHeightPx?: number;
  naturalWidthPt?: number;
  naturalHeightPt?: number;
};

type CssBox = {
  left: string;
  top: string;
  width: string;
  height: string;
};

// Mock react-pdf: render stub Document and Page components that just render their children
vi.mock("react-pdf", () => ({
  Document: ({ children }: DocumentMockProps) => (
    <div data-testid="pdf-document">
      {children}
    </div>
  ),
  Page: ({ children, pageNumber }: PageMockProps) => (
    // Do NOT call onLoadSuccess synchronously — it triggers setPageDims which
    // causes a render loop in jsdom. The text-preview strip tests don't need pageDims.
    <div data-testid={`pdf-page-${pageNumber}`}>
      Page {pageNumber}
      {children}
    </div>
  ),
}));

// Mock the pdfWorker module (side-effect only)
vi.mock("@/lib/pdfWorker", () => ({}));

// Mock the bbox conversion utilities
vi.mock("@/lib/bboxConversion", () => ({
  findOverlayChunk: (
    chunks: Array<ChunkManifestEntry>,
    citation: SelectedCitation | null,
    pageNum: number | null
  ): ChunkManifestEntry | null => {
    if (!citation || !chunks || !pageNum) return null;
    // Return a mock chunk that matches the current page
    const matchingChunk = chunks.find(
      (c: ChunkManifestEntry) =>
        c.page_start !== null &&
        pageNum >= c.page_start &&
        (!c.page_end || pageNum <= c.page_end)
    );
    return matchingChunk || null;
  },
  bboxToCssBox: (
    bbox: [number, number, number, number],
    dims: BboxDims
  ): CssBox => {
    // Simple mock: just return proportional CSS values
    const [x0, top, x1, bottom] = bbox;
    const pageWidthPx = dims.pageWidthPx || 580;
    const pageHeightPx = dims.pageHeightPx || 700;
    const naturalWidthPt = dims.naturalWidthPt || 612;
    const naturalHeightPt = dims.naturalHeightPt || 792;

    return {
      left: `${(x0 / naturalWidthPt) * pageWidthPx}px`,
      top: `${(top / naturalHeightPt) * pageHeightPx}px`,
      width: `${((x1 - x0) / naturalWidthPt) * pageWidthPx}px`,
      height: `${((bottom - top) / naturalHeightPt) * pageHeightPx}px`,
    };
  },
  isFullPageBbox: (
    bbox: [number, number, number, number],
    width: number,
    height: number
  ): boolean => {
    // Mirror real implementation: both axes independently must be >= 0.9
    const [x0, top, x1, bottom] = bbox;
    const widthRatio = (x1 - x0) / width;
    const heightRatio = (bottom - top) / height;
    return widthRatio >= 0.9 && heightRatio >= 0.9;
  },
}));

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockChunksResponse: ChunksResponse = {
  document_id: "doc123",
  chunks: [
    {
      chunk_index: 0,
      page_start: 1,
      page_end: 1,
      bbox: [100, 200, 400, 300],
      section_path: "Introduction",
      text_preview: "This is the introduction text of the document.",
    },
    {
      chunk_index: 1,
      page_start: 2,
      page_end: 2,
      bbox: [50, 100, 500, 200],
      section_path: "Main Content",
      text_preview: "This is the main content paragraph.",
    },
    {
      chunk_index: 2,
      page_start: 3,
      page_end: 3,
      bbox: null,
      section_path: null,
      text_preview: "",
    },
  ],
};

const mockCitation: SelectedCitation = {
  documentId: "doc123",
  documentName: "test-document.pdf",
  pageStart: 1,
  pageEnd: 2,
  chunkIndex: 0,
};

describe("SourcePanel", () => {
  beforeEach(() => {
    mockFetch.mockClear();
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockChunksResponse,
    });
    // Radix UI leaves body attributes after a Sheet unmounts in jsdom; reset them.
    document.body.removeAttribute("data-scroll-locked");
    document.body.style.removeProperty("pointer-events");
  });

  it("renders null when citation is null", () => {
    const { container } = render(<SourcePanel citation={null} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("AC3: renders 'Cited passage' heading when text_preview is present", async () => {
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    // Wait for the component to fetch chunks
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // The "Cited passage" heading should appear
    expect(screen.getByText("Cited passage")).toBeInTheDocument();
  });

  it("AC3: displays text preview when chunk has text_preview", async () => {
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // The text preview should render
    expect(screen.getByText("This is the introduction text of the document.")).toBeInTheDocument();
  });

  it("AC3: hides the text preview strip when text_preview is empty", async () => {
    // Modify citation to point to chunk with empty text_preview
    const citationToEmptyChunk: SelectedCitation = {
      documentId: "doc123",
      documentName: "test-document.pdf",
      pageStart: 3,
      pageEnd: 3,
      chunkIndex: 2,
    };

    render(<SourcePanel citation={citationToEmptyChunk} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // "Cited passage" should NOT appear
    expect(screen.queryByText("Cited passage")).not.toBeInTheDocument();
  });

  it("AC3: hides the text preview strip when no chunk matches", async () => {
    // Citation that doesn't match any chunk
    const unmatchedCitation: SelectedCitation = {
      documentId: "doc123",
      documentName: "test-document.pdf",
      pageStart: 99,
      pageEnd: 99,
      chunkIndex: 99,
    };

    render(<SourcePanel citation={unmatchedCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // "Cited passage" should NOT appear
    expect(screen.queryByText("Cited passage")).not.toBeInTheDocument();
  });

  it("AC3: fetches chunks from the correct API endpoint", async () => {
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/documents/doc123/chunks"),
        expect.any(Object)
      );
    });
  });

  it("AC3: handles fetch errors gracefully (no chunks rendered)", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Should not crash; "Cited passage" should not appear
    expect(screen.queryByText("Cited passage")).not.toBeInTheDocument();
  });

  it("AC3: handles malformed chunks response gracefully", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ chunks: undefined }),
    });

    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Should not crash
    expect(screen.queryByText("Cited passage")).not.toBeInTheDocument();
  });

  it("AC1: opens Sheet when citation is provided", async () => {
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    // The Sheet should be open (check for document name in header)
    expect(screen.getByText("test-document.pdf")).toBeInTheDocument();
  });

  it("AC1: displays page range in header", async () => {
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    // Should show the page range
    expect(screen.getByText("Pages 1–2")).toBeInTheDocument();
  });

  it("AC1: displays single page indicator when pageStart equals pageEnd", async () => {
    const singlePageCitation: SelectedCitation = {
      documentId: "doc123",
      documentName: "test-document.pdf",
      pageStart: 5,
      pageEnd: 5,
      chunkIndex: 0,
    };

    render(<SourcePanel citation={singlePageCitation} onClose={vi.fn()} />);

    expect(screen.getByText("Page 5", { selector: "p" })).toBeInTheDocument();
  });

  it("AC2: calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<SourcePanel citation={mockCitation} onClose={onClose} />);

    // SheetContent adds its own close button; getAllByRole returns both — take the first (Sheet's built-in X)
    const closeButton = screen.getAllByRole("button", { name: "Close" })[0];
    await user.click(closeButton);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("AC2: disables Previous button on first page", async () => {
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    const prevButton = screen.getByRole("button", { name: /Previous/ });
    expect(prevButton).toBeDisabled();
  });

  it("AC2: disables Next button on last page", async () => {
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Navigate to the last page
    const nextButton = screen.getByRole("button", { name: /Next/ });
    await userEvent.setup().click(nextButton);

    // Now Next should be disabled
    expect(nextButton).toBeDisabled();
  });

  it("AC2: footer shows 'Page N · cited pp.X–Y' for multi-page citation", async () => {
    const multiPageCitation: SelectedCitation = {
      documentId: "doc123",
      documentName: "test-document.pdf",
      pageStart: 3,
      pageEnd: 7,
      chunkIndex: 0,
    };

    render(<SourcePanel citation={multiPageCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Footer span shows current page + cited range
    // { selector: "span" } ensures we match the footer element, not any other node that
    // might incidentally contain this string. Use Unicode escapes so en-dash (U+2013)
    // and middle-dot (U+00B7) are unambiguous.
    expect(screen.getByText("Page 3 · cited pp.3–7", { selector: "span" })).toBeInTheDocument();
  });

  it("AC2: footer shows 'Page N' only for single-page citation", async () => {
    const singlePageCitation: SelectedCitation = {
      documentId: "doc123",
      documentName: "test-document.pdf",
      pageStart: 5,
      pageEnd: 5,
      chunkIndex: 0,
    };

    render(<SourcePanel citation={singlePageCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Footer shows page only — no range suffix
    expect(screen.getByText("Page 5", { selector: "span" })).toBeInTheDocument();
    // Confirm no "· cited" suffix — regex doesn't care about encoding
    expect(screen.queryByText(/cited pp\./)).not.toBeInTheDocument();
  });
});
