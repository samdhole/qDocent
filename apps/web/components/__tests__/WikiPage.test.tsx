import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import WikiPage from "../WikiPage";

// MermaidDiagram uses browser APIs; replace with a test double
vi.mock("../MermaidDiagram", () => ({
  default: ({ chart }: { chart: string }) => (
    <div data-testid="mermaid-diagram">{chart}</div>
  ),
}));

describe("WikiPage", () => {
  it("renders the page title", () => {
    render(<WikiPage title="Overview" content="Hello" sourceDocIds={[]} />);
    expect(
      screen.getByRole("heading", { name: "Overview" })
    ).toBeInTheDocument();
  });

  it("renders plain markdown content", () => {
    render(<WikiPage title="T" content="Some **bold** text" sourceDocIds={[]} />);
    expect(screen.getByText("bold")).toBeInTheDocument();
  });

  it("delegates mermaid code blocks to MermaidDiagram", () => {
    const content = "```mermaid\ngraph TD; A-->B\n```";
    render(<WikiPage title="T" content={content} sourceDocIds={[]} />);
    expect(screen.getByTestId("mermaid-diagram")).toBeInTheDocument();
  });

  it("shows source doc IDs when present", () => {
    render(
      <WikiPage title="T" content="text" sourceDocIds={["abc123def456"]} />
    );
    expect(screen.getByText(/abc123def4/)).toBeInTheDocument();
  });

  it("hides source section when sourceDocIds is empty", () => {
    render(<WikiPage title="T" content="text" sourceDocIds={[]} />);
    expect(screen.queryByText("SOURCE DOCUMENTS")).not.toBeInTheDocument();
  });
});
