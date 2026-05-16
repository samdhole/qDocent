import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SourcePanel from "../SourcePanel";
import type { ChunksResponse, SelectedCitation } from "@/lib/types";

// Mock react-pdf: render stub Document and Page components that just render their children
vi.mock("react-pdf", () => ({
  Document: ({ children, file, loading, error }: any) => (
    <div data-testid="pdf-document">
      {children}
    </div>
  ),
  Page: ({ children, pageNumber }: any) => (
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
  findOverlayChunk: (chunks: any[], citation: any, pageNum: any) => {
    if (!citation || !chunks || !pageNum) return null;
    // Return a mock chunk that matches the current page
    const matchingChunk = chunks.find(
      (c: any) =>
        c.page_start !== null &&
        pageNum >= c.page_start &&
        (!c.page_end || pageNum <= c.page_end)
    );
    return matchingChunk || null;
  },
  bboxToCssBox: (bbox: [number, number, number, number], dims: any) => {
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
  isFullPageBbox: (bbox: [number, number, number, number], width: number, height: number) => {
    // Consider full page if bbox covers >90% of the page
    const [x0, top, x1, bottom] = bbox;
    const areaRatio = ((x1 - x0) * (bottom - top)) / (width * height);
    return areaRatio > 0.9;
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
    // Default mock response for chunks
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockChunksResponse,
    });
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

  it("AC2: navigates to next page when Next button is clicked", async () => {
    const user = userEvent.setup();
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Get the pagination display to verify initial state
    const paginationText = screen.getByText(/1 of 2/);
    expect(paginationText).toBeInTheDocument();

    const nextButton = screen.getByRole("button", { name: /Next/ });
    await user.click(nextButton);

    // After clicking Next, pagination should update to show page 2
    expect(screen.getByText(/2 of 2/)).toBeInTheDocument();
  });

  it("AC2: navigates to previous page when Previous button is clicked", async () => {
    const user = userEvent.setup();
    render(<SourcePanel citation={mockCitation} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Click Next to get to page 2
    const nextButton = screen.getByRole("button", { name: /Next/ });
    await user.click(nextButton);

    expect(screen.getByText(/2 of 2/)).toBeInTheDocument();

    // Click Previous to go back to page 1
    const prevButton = screen.getByRole("button", { name: /Previous/ });
    await user.click(prevButton);

    expect(screen.getByText(/1 of 2/)).toBeInTheDocument();
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
});
