import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WikiGenerateButton from "../WikiGenerateButton";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("WikiGenerateButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
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
});
