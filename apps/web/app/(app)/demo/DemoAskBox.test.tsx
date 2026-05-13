import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { DemoAskBox } from "./DemoAskBox";

// Mock the imported components
vi.mock("@/components/ConversationView", () => ({
  default: () => <div data-testid="conversation-view">ConversationView</div>,
}));

vi.mock("@/components/AnswerCard", () => ({
  default: ({ result }: any) => (
    <div data-testid="answer-card">
      {result.question}: {result.answer}
    </div>
  ),
}));

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children, variant }: any) => (
    <div data-testid="badge" data-variant={variant}>
      {children}
    </div>
  ),
}));

// Mock the example QA data
vi.mock("./data/example_qa.json", () => ({
  default: {
    question: "What is this company's annual revenue?",
    answer: "The company reported total revenue of [1] $1.82 billion...",
    citations: [],
    retrieved_contexts: [],
    figures: [],
    confidence_label: "high",
    needs_human_review: false,
  },
}));

describe("DemoAskBox", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading skeleton initially", () => {
    // Set up: mock fetch that will never resolve quickly
    (global.fetch as any).mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () => resolve({ ok: true }),
            10000 // resolve after 10s, longer than any test
          )
        )
    );

    vi.stubEnv("NEXT_PUBLIC_DEMO_NOTEBOOK_ID", "test-notebook-id");

    const { container } = render(<DemoAskBox />);

    // Verify: loading skeleton (animate-pulse div) is shown
    const skeleton = container.querySelector(".animate-pulse");
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveClass("h-24", "bg-card", "rounded-lg");
  });

  it("shows ConversationView when API is healthy", async () => {
    // Set up: mock successful health check
    (global.fetch as any).mockResolvedValueOnce({ ok: true });

    vi.stubEnv("NEXT_PUBLIC_DEMO_NOTEBOOK_ID", "test-notebook-id");

    render(<DemoAskBox />);

    // Verify: after health check succeeds, ConversationView is rendered
    await waitFor(() => {
      expect(screen.getByTestId("conversation-view")).toBeInTheDocument();
    });
  });

  it("shows cached answer when API is unavailable (health check fails)", async () => {
    // Set up: mock failed health check
    (global.fetch as any).mockRejectedValueOnce(new Error("Network error"));

    vi.stubEnv("NEXT_PUBLIC_DEMO_NOTEBOOK_ID", "test-notebook-id");

    render(<DemoAskBox />);

    // Verify: after health check fails, AnswerCard and offline badge are rendered
    await waitFor(() => {
      expect(screen.getByTestId("answer-card")).toBeInTheDocument();
      expect(screen.getByTestId("badge")).toHaveTextContent(
        /Live demo unavailable/
      );
    });
  });

  it("shows cached answer when notebook ID is unset", async () => {
    // Set up: no notebook ID
    vi.stubEnv("NEXT_PUBLIC_DEMO_NOTEBOOK_ID", "");

    render(<DemoAskBox />);

    // Verify: immediately shows offline state without waiting for health check
    await waitFor(() => {
      expect(screen.getByTestId("answer-card")).toBeInTheDocument();
      expect(screen.getByTestId("badge")).toHaveTextContent(
        /Live demo unavailable/
      );
    });

    // Verify: fetch was never called
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("calls health endpoint with correct URL and timeout", async () => {
    // Set up
    (global.fetch as any).mockResolvedValueOnce({ ok: true });
    vi.stubEnv("NEXT_PUBLIC_DEMO_NOTEBOOK_ID", "test-notebook-id");

    render(<DemoAskBox />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/health",
        expect.objectContaining({
          signal: expect.any(AbortSignal),
        })
      );
    });
  });

  it("shows cached answer when health check returns non-200 status", async () => {
    // Set up: mock health check returning error status
    (global.fetch as any).mockResolvedValueOnce({ ok: false });

    vi.stubEnv("NEXT_PUBLIC_DEMO_NOTEBOOK_ID", "test-notebook-id");

    render(<DemoAskBox />);

    // Verify: AnswerCard is rendered (offline state)
    await waitFor(() => {
      expect(screen.getByTestId("answer-card")).toBeInTheDocument();
      expect(screen.getByTestId("badge")).toHaveTextContent(
        /Live demo unavailable/
      );
    });
  });
});
