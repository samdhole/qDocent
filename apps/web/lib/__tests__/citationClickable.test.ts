import { describe, expect, it, vi } from "vitest";
import { canOpenSource } from "../citationClickable";

describe("canOpenSource", () => {
  const cb = vi.fn();

  it("is clickable when all three conditions are met", () => {
    expect(canOpenSource({ document_id: "doc-123", page: 1 } as any, cb)).toBe(true);
  });

  it("is NOT clickable when document_id is undefined", () => {
    expect(canOpenSource({ document_id: undefined, page: 1 } as any, cb)).toBe(false);
  });

  it("is NOT clickable when document_id is null", () => {
    expect(canOpenSource({ document_id: null, page: 1 } as any, cb)).toBe(false);
  });

  it("is NOT clickable when page is null", () => {
    expect(canOpenSource({ document_id: "doc-123", page: null } as any, cb)).toBe(false);
  });

  it("is NOT clickable when page is undefined", () => {
    expect(canOpenSource({ document_id: "doc-123", page: undefined } as any, cb)).toBe(false);
  });

  it("is NOT clickable when onSelectCitation is undefined", () => {
    expect(canOpenSource({ document_id: "doc-123", page: 1 } as any, undefined)).toBe(false);
  });

  it("page=0 is treated as non-clickable (1-indexed pages assumed)", () => {
    // page=0 is falsy — documents assume 1-indexed pages so 0 is not a valid target.
    expect(canOpenSource({ document_id: "doc-123", page: 0 } as any, cb)).toBe(false);
  });
});
