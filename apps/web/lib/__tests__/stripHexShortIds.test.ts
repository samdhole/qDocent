import { describe, expect, it } from "vitest";
import { stripHexShortIds } from "../stripHexShortIds";

describe("stripHexShortIds", () => {
  it("strips lowercase 6-char hex id", () => {
    expect(stripHexShortIds("Based on policy [aeab962] the answer is yes.")).toBe(
      "Based on policy the answer is yes."
    );
  });

  it("strips uppercase 8-char hex id", () => {
    expect(stripHexShortIds("See [A1B2C3D4] for details.")).toBe("See for details.");
  });

  it("strips mixed-case 7-char hex id", () => {
    expect(stripHexShortIds("Source [aB3f12e] confirms this.")).toBe("Source confirms this.");
  });

  it("does NOT strip numeric citation marker [1]", () => {
    expect(stripHexShortIds("According to [1] the rule applies.")).toBe(
      "According to [1] the rule applies."
    );
  });

  it("does NOT strip numeric citation marker [12]", () => {
    expect(stripHexShortIds("See [12] and [3] for more.")).toBe("See [12] and [3] for more.");
  });

  it("strips leading space before id when present", () => {
    expect(stripHexShortIds("Text [aeab962] end.")).toBe("Text end.");
  });

  it("strips id at start of string", () => {
    expect(stripHexShortIds("[aeab962] is the source.")).toBe(" is the source.");
  });
});
