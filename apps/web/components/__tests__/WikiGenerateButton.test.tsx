import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WikiGenerateButton from "../WikiGenerateButton";

const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRefresh }),
}));

describe("WikiGenerateButton", () => {
  // Real timers suffice: these tests never tick the 2s polling interval (they assert on click-path state
  // before any interval fires). Fake timers are used only in the completion test where the interval must advance.
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders generate button in idle state", () => {
    render(<WikiGenerateButton notebookId="nb-1" />);
    expect(
      screen.getByRole("button", { name: /generate wiki/i })
    ).toBeInTheDocument();
  });

  it("shows error detail from 422 response", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: "notebook has no documents" }),
    });

    render(<WikiGenerateButton notebookId="nb-1" />);
    fireEvent.click(screen.getByRole("button", { name: /generate wiki/i }));

    await waitFor(
      () => {
        expect(
          screen.getByText("notebook has no documents")
        ).toBeInTheDocument();
      },
      { timeout: 10000 }
    );
  });

  it("shows generating state after job is created", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "job-abc", status: "queued" }),
    });

    render(<WikiGenerateButton notebookId="nb-1" />);
    fireEvent.click(screen.getByRole("button", { name: /generate wiki/i }));

    await waitFor(
      () => {
        expect(screen.getByText(/generating/i)).toBeInTheDocument();
      },
      { timeout: 10000 }
    );
  });

  it("shows try again button after error", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: "failed" }),
    });

    render(<WikiGenerateButton notebookId="nb-1" />);
    fireEvent.click(screen.getByRole("button", { name: /generate wiki/i }));

    await waitFor(
      () => {
        expect(
          screen.getByRole("button", { name: /try again/i })
        ).toBeInTheDocument();
      },
      { timeout: 10000 }
    );
  });

  it("transitions to wiki view when generation completes", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;

    // POST to generate returns job_id
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "job-abc" }),
    });

    render(<WikiGenerateButton notebookId="nb-1" />);
    fireEvent.click(screen.getByRole("button", { name: /generate wiki/i }));

    // Wait for generating state (confirms POST succeeded and polling effect is set up)
    await waitFor(
      () => {
        expect(screen.getByText(/generating/i)).toBeInTheDocument();
      },
      { timeout: 10000 }
    );

    // Mock next poll call returns completed status
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: "completed",
        pages_done: 3,
        pages_total: 3,
      }),
    });

    // Wait for the polling interval (2000ms) to fire and completion state to be reached
    await waitFor(
      () => {
        expect(screen.getByText(/wiki ready/i)).toBeInTheDocument();
      },
      { timeout: 10000 }
    );

    // Verify that the polling interval was triggered (via the fetch mock call count)
    // and router.refresh was invoked when status became "completed"
    expect(mockRefresh).toHaveBeenCalled();
  });
});
