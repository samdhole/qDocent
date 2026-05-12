import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import WikiTreeNav from "../WikiTreeNav";

const structure = {
  title: "My Wiki",
  sections: [
    {
      title: "Getting Started",
      pages: [
        { slug: "intro", title: "Introduction" },
        { slug: "setup", title: "Setup Guide" },
      ],
    },
  ],
};

describe("WikiTreeNav", () => {
  it("renders wiki title", () => {
    render(<WikiTreeNav notebookId="nb-1" structure={structure} />);
    expect(screen.getByText("My Wiki")).toBeInTheDocument();
  });

  it("renders section heading", () => {
    render(<WikiTreeNav notebookId="nb-1" structure={structure} />);
    expect(screen.getByText("Getting Started")).toBeInTheDocument();
  });

  it("renders page links with correct href", () => {
    render(<WikiTreeNav notebookId="nb-1" structure={structure} />);
    const link = screen.getByRole("link", { name: "Introduction" });
    expect(link).toHaveAttribute("href", "/notebooks/nb-1/wiki/intro");
  });

  it("applies active style to the active slug", () => {
    render(
      <WikiTreeNav notebookId="nb-1" structure={structure} activeSlug="intro" />
    );
    const activeLink = screen.getByRole("link", { name: "Introduction" });
    expect(activeLink.className).toMatch(/bg-accent/);
  });

  it("does not apply active style to other pages", () => {
    render(
      <WikiTreeNav notebookId="nb-1" structure={structure} activeSlug="intro" />
    );
    const otherLink = screen.getByRole("link", { name: "Setup Guide" });
    expect(otherLink.className).not.toMatch(/bg-accent\s/);
  });
});
