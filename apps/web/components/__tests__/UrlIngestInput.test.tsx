import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UrlIngestInput } from "../UrlIngestInput";
import * as sonner from "sonner";

vi.mock("sonner");

const mockFetch = vi.fn();
global.fetch = mockFetch as any;

describe("UrlIngestInput", () => {
  beforeEach(() => {
    mockFetch.mockClear();
    vi.clearAllMocks();
  });

  it("renders the URL input and Ingest URL button", () => {
    render(<UrlIngestInput notebookId="nb-1" />);
    expect(screen.getByPlaceholderText(/https:\/\/example\.com/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ingest URL/ })).toBeInTheDocument();
  });

  it("button is disabled when input is empty", () => {
    render(<UrlIngestInput notebookId="nb-1" />);
    expect(screen.getByRole("button", { name: /Ingest URL/ })).toBeDisabled();
  });

  it("shows success toast and clears input on 2xx response (AC3.1)", async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({ ok: true });

    render(<UrlIngestInput notebookId="nb-1" />);
    const input = screen.getByPlaceholderText(/https:\/\/example\.com/) as HTMLInputElement;
    await user.type(input, "https://example.com/article");
    await user.click(screen.getByRole("button", { name: /Ingest URL/ }));

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/notebooks/nb-1/ingest/url"),
      expect.objectContaining({ method: "POST" })
    );
    expect(input.value).toBe("");
    expect(vi.mocked(sonner.toast.success)).toHaveBeenCalledWith(
      expect.stringContaining("ingested")
    );
    expect(vi.mocked(sonner.toast.error)).not.toHaveBeenCalled();
  });

  it("shows error toast and keeps input value on failure (AC3.2)", async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({ ok: false, status: 502 });

    render(<UrlIngestInput notebookId="nb-1" />);
    const input = screen.getByPlaceholderText(/https:\/\/example\.com/) as HTMLInputElement;
    await user.type(input, "https://bad-url.example");
    await user.click(screen.getByRole("button", { name: /Ingest URL/ }));

    expect(vi.mocked(sonner.toast.error)).toHaveBeenCalled();
    expect(vi.mocked(sonner.toast.success)).not.toHaveBeenCalled();
    // Input is NOT cleared on failure
    expect(input.value).toBe("https://bad-url.example");
  });

  it("disables button and shows loading text while in-flight (AC3.3)", async () => {
    const user = userEvent.setup();
    let resolve!: (value: { ok: boolean }) => void;
    mockFetch.mockReturnValueOnce(
      new Promise<{ ok: boolean }>((r) => {
        resolve = r;
      })
    );

    render(<UrlIngestInput notebookId="nb-1" />);
    const input = screen.getByPlaceholderText(/https:\/\/example\.com/) as HTMLInputElement;
    await user.type(input, "https://example.com");

    const button = screen.getByRole("button", { name: /Ingest URL/ });
    expect(button).not.toBeDisabled();

    await user.click(button);

    // While in flight: button should show "Ingesting…" and be disabled
    expect(screen.getByRole("button", { name: /Ingesting/ })).toBeDisabled();

    // Resolve the promise and wait for state updates
    resolve({ ok: true });

    // After resolution, button should say "Ingest URL" again (input was cleared)
    // and be disabled because input is empty
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Ingest URL/ })).toBeDisabled();
    });
  });

  it("shows error toast on network failure (AC3.2)", async () => {
    const user = userEvent.setup();
    mockFetch.mockRejectedValueOnce(new Error("network error"));

    render(<UrlIngestInput notebookId="nb-1" />);
    await user.type(screen.getByPlaceholderText(/https:\/\/example\.com/), "https://example.com");
    await user.click(screen.getByRole("button", { name: /Ingest URL/ }));

    expect(await screen.findByRole("button", { name: /Ingest URL/ })).toBeInTheDocument();
    expect(vi.mocked(sonner.toast.error)).toHaveBeenCalled();
  });

  it("submits on Enter key (AC3.1)", async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({ ok: true });

    render(<UrlIngestInput notebookId="nb-1" />);
    const input = screen.getByPlaceholderText(/https:\/\/example\.com/);
    await user.type(input, "https://example.com{Enter}");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/notebooks/nb-1/ingest/url"),
      expect.objectContaining({ method: "POST" })
    );
  });
});
