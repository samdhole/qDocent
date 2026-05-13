import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { DemoAskBox } from "./DemoAskBox";
import type { AskResponse } from "@/lib/types";

// Mock the imported components
vi.mock("@/components/ConversationView", () => ({
  default: () => <div data-testid="conversation-view">ConversationView</div>,
}));

vi.mock("@/components/AnswerCard", () => ({
  default: ({ result }: { result: AskResponse }) => (
    <div data-testid="answer-card">
      {result.question}: {result.answer}
    </div>
  ),
}));

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children, variant }: { children: React.ReactNode; variant?: string }) => (
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
  const mockFetch = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading skeleton initially", () => {
    // Set up: mock fetch that will never resolve quickly
    mockFetch.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () => resolve(new Response(JSON.stringify({ ok: true }), { status: 200 })),
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
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));

    vi.stubEnv("NEXT_PUBLIC_DEMO_NOTEBOOK_ID", "test-notebook-id");

    render(<DemoAskBox />);

    // Verify: after health check succeeds, ConversationView is rendered
    await waitFor(() => {
      expect(screen.getByTestId("conversation-view")).toBeInTheDocument();
    });
  });

  it("shows cached answer when API is unavailable (health check fails)", async () => {
    // Set up: mock failed health check
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

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
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("calls health endpoint with correct URL and timeout", async () => {
    // Set up
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
    vi.stubEnv("NEXT_PUBLIC_DEMO_NOTEBOOK_ID", "test-notebook-id");

    render(<DemoAskBox />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/health",
        expect.objectContaining({
          signal: expect.any(AbortSignal),
        })
      );
    });
  });

  it("shows cached answer when health check returns non-200 status", async () => {
    // Set up: mock health check returning error status
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify({ status: "error" }), { status: 500 }));

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
