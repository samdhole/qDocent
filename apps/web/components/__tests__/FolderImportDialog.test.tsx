import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FolderImportDialog } from "../FolderImportDialog";

// --- Mocks ---

const mockStart = vi.fn();
const mockBatchState = {
  items: [] as Array<{ id: string; file: File; status: string; error?: string }>,
  total: 0,
  done: 0,
  failed: 0,
  batchStatus: "idle" as "idle" | "running" | "complete",
  start: mockStart,
};

vi.mock("@/lib/useBatchUpload", () => ({
  useBatchUpload: () => mockBatchState,
}));

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

// --- Helpers ---

function makeFile(name: string, path?: string): File & { webkitRelativePath?: string } {
  const file = new File(["content"], name, { type: "application/pdf" }) as File & { webkitRelativePath?: string };
  if (path) {
    Object.defineProperty(file, "webkitRelativePath", {
      value: path,
      writable: true,
    });
  }
  return file;
}

function defaultProps() {
  return {
    open: true,
    onOpenChange: vi.fn(),
    onImported: vi.fn(),
  };
}

// Simulate webkitdirectory file input change
function fireFileInput(files: Array<File & { webkitRelativePath?: string }>) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  // jsdom doesn't support webkitdirectory, but the onChange fires normally
  Object.defineProperty(input, "files", {
    value: files,
    configurable: true,
  });
  fireEvent.change(input);
}

// --- Tests ---

describe("FolderImportDialog", () => {
  beforeEach(() => {
    mockFetch.mockClear();
    mockStart.mockClear();
    mockPush.mockClear();
    mockBatchState.batchStatus = "idle";
    mockBatchState.items = [];
    mockBatchState.total = 0;
    mockBatchState.done = 0;
    mockBatchState.failed = 0;
  });

  it("renders step 1 (pick) by default (AC1.2)", () => {
    render(<FolderImportDialog {...defaultProps()} />);
    expect(screen.getByText("Select Folder")).toBeInTheDocument();
    expect(screen.getByText("Choose Folder")).toBeInTheDocument();
  });

  it("shows file count and filtered count after folder selected (AC1.3)", () => {
    render(<FolderImportDialog {...defaultProps()} />);
    const pdfFile = makeFile("doc.pdf", "myfolder/doc.pdf");
    const txtFile = makeFile("notes.txt", "myfolder/notes.txt");
    fireFileInput([pdfFile, txtFile]);
    expect(screen.getByText(/1 file.*ready/)).toBeInTheDocument();
    expect(screen.getByText(/1 unsupported skipped/)).toBeInTheDocument();
  });

  it("Next button disabled when no valid files selected (AC1.3)", () => {
    render(<FolderImportDialog {...defaultProps()} />);
    const next = screen.getByRole("button", { name: /Next/ });
    expect(next).toBeDisabled();
  });

  it("Next button enabled after valid files selected (AC1.3)", () => {
    render(<FolderImportDialog {...defaultProps()} />);
    fireFileInput([makeFile("doc.pdf", "myfolder/doc.pdf")]);
    expect(screen.getByRole("button", { name: /Next/ })).not.toBeDisabled();
  });

  it("advances to step 2 on Next click", async () => {
    const user = userEvent.setup();
    render(<FolderImportDialog {...defaultProps()} />);
    fireFileInput([makeFile("doc.pdf", "myfolder/doc.pdf")]);
    await user.click(screen.getByRole("button", { name: /Next/ }));
    expect(screen.getByText("Name Your Notebook")).toBeInTheDocument();
  });

  it("Start Import disabled when name is empty (AC1.10)", async () => {
    const user = userEvent.setup();
    render(<FolderImportDialog {...defaultProps()} />);
    fireFileInput([makeFile("doc.pdf", "myfolder/doc.pdf")]);
    await user.click(screen.getByRole("button", { name: /Next/ }));
    // Clear the prefilled name
    const nameInput = screen.getByPlaceholderText("Notebook name") as HTMLInputElement;
    await user.clear(nameInput);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Start Import/ })).toBeDisabled();
    });
  });

  it("shows error and stays on step 2 when POST /notebooks fails (AC1.11)", async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({ ok: false, status: 503 });
    render(<FolderImportDialog {...defaultProps()} />);
    fireFileInput([makeFile("doc.pdf", "myfolder/doc.pdf")]);
    await user.click(screen.getByRole("button", { name: /Next/ }));
    await user.click(screen.getByRole("button", { name: /Start Import/ }));
    // Wait for the error message to appear
    await waitFor(() => {
      expect(screen.getByText(/Failed to create notebook/)).toBeInTheDocument();
    });
    expect(screen.getByText("Name Your Notebook")).toBeInTheDocument();
  });

  it("calls start() with files and notebookId after successful POST /notebooks", async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "nb-123" }),
    });
    render(<FolderImportDialog {...defaultProps()} />);
    const file = makeFile("doc.pdf", "myfolder/doc.pdf");
    fireFileInput([file]);
    await user.click(screen.getByRole("button", { name: /Next/ }));
    await user.click(screen.getByRole("button", { name: /Start Import/ }));
    // Wait for the mock to be called
    await waitFor(() => {
      expect(mockStart).toHaveBeenCalledWith([file], "nb-123");
    });
  });

  it("disables Cancel while upload is running (AC1.9)", async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "nb-123" }),
    });
    render(<FolderImportDialog {...defaultProps()} />);
    fireFileInput([makeFile("doc.pdf", "myfolder/doc.pdf")]);
    await user.click(screen.getByRole("button", { name: /Next/ }));

    // Set running state before the POST resolves
    mockBatchState.batchStatus = "running";
    await user.click(screen.getByRole("button", { name: /Start Import/ }));

    // Progress step should show disabled Cancel
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Cancel/ })).toBeDisabled();
    });
  });

  it("Generate Wiki fires POST /notebooks/{id}/wiki fire-and-forget and closes dialog (AC1.7)", async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    // Successful notebook creation
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "nb-456" }),
    });
    // wiki POST (fire-and-forget)
    mockFetch.mockResolvedValue({ ok: true });

    const { rerender } = render(<FolderImportDialog {...props} />);
    fireFileInput([makeFile("doc.pdf", "myfolder/doc.pdf")]);
    await user.click(screen.getByRole("button", { name: /Next/ }));
    await user.click(screen.getByRole("button", { name: /Start Import/ }));

    // Simulate batch completion by mutating mock state and re-rendering
    // (useEffect watches batchStatus; rerender gives component the new value)
    mockBatchState.batchStatus = "complete";
    rerender(<FolderImportDialog {...props} />);

    // Step "done" is now active — Generate Wiki button visible
    const wikiButton = await screen.findByRole("button", { name: /Generate Wiki/ });
    await user.click(wikiButton);

    // wiki POST was fired
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/notebooks/nb-456/wiki"),
      expect.objectContaining({ method: "POST" })
    );
    // dialog closed via onOpenChange
    expect(props.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("View Notebook → navigates to /notebooks/{id} (AC1.8)", async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "nb-789" }),
    });

    const { rerender } = render(<FolderImportDialog {...props} />);
    fireFileInput([makeFile("doc.pdf", "myfolder/doc.pdf")]);
    await user.click(screen.getByRole("button", { name: /Next/ }));
    await user.click(screen.getByRole("button", { name: /Start Import/ }));

    // Simulate batch completion
    mockBatchState.batchStatus = "complete";
    rerender(<FolderImportDialog {...props} />);

    const viewButton = await screen.findByRole("button", { name: /View Notebook/ });
    await user.click(viewButton);

    expect(mockPush).toHaveBeenCalledWith("/notebooks/nb-789");
    expect(props.onOpenChange).toHaveBeenCalledWith(false);
  });
});
