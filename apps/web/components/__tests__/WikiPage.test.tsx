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
  it("renders the page title from markdown content", () => {
    render(<WikiPage title="Overview" content={"# Overview\n\nHello"} sourceDocIds={[]} />);
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
    expect(screen.getByText(/abc123de/)).toBeInTheDocument();
  });

  it("hides source section when sourceDocIds is empty", () => {
    render(<WikiPage title="T" content="text" sourceDocIds={[]} />);
    expect(screen.queryByText("SOURCE DOCUMENTS")).not.toBeInTheDocument();
  });

  it("renders resolved doc name as clickable badge", () => {
    render(
      <WikiPage
        title="Test"
        content="content"
        sourceDocIds={["abc-123"]}
        docNames={{ "abc-123": "report.pdf" }}
      />
    );
    const badge = screen.getByRole("link", { name: "report.pdf" });
    expect(badge).toHaveAttribute("href", expect.stringContaining("/documents/abc-123/source"));
    expect(badge).toHaveAttribute("target", "_blank");
  });

  it("falls back to short ID when docName missing", () => {
    render(
      <WikiPage
        title="Test"
        content="content"
        sourceDocIds={["deadbeef-1234-5678-abcd-000000000000"]}
        docNames={{}}
      />
    );
    expect(screen.getByText(/deadbeef/)).toBeInTheDocument();
  });

  it("wiki cross-links use Next.js Link without target blank", () => {
    render(
      <WikiPage
        title="Test"
        content="See [Architecture](/notebooks/nb-1/wiki/architecture) for details."
        sourceDocIds={[]}
        docNames={{}}
      />
    );
    const link = screen.getByRole("link", { name: "Architecture" });
    expect(link).toHaveAttribute("href", "/notebooks/nb-1/wiki/architecture");
    expect(link).not.toHaveAttribute("target", "_blank");
  });

  it("external links open in new tab", () => {
    render(
      <WikiPage
        title="Test"
        content="Visit [Example](https://example.com) for more."
        sourceDocIds={[]}
        docNames={{}}
      />
    );
    const link = screen.getByRole("link", { name: "Example" });
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).toHaveAttribute("target", "_blank");
  });
});
