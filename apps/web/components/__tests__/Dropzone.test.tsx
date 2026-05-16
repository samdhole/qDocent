import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Dropzone } from "../Dropzone";
import { NOTEBOOK_ACCEPT } from "@/lib/acceptedTypes";
import * as sonner from "sonner";

type DropzoneOptions = {
  accept?: Record<string, Array<string>>;
  onDrop?: (accepted: Array<File>, rejected: Array<unknown>) => void;
};

let capturedOptions: DropzoneOptions = {};

vi.mock("sonner");

vi.mock("react-dropzone", () => ({
  useDropzone: (opts: DropzoneOptions) => {
    capturedOptions = opts;
    return {
      getRootProps: () => ({ "data-testid": "dropzone-root" }),
      getInputProps: () => ({}),
      isDragActive: false,
    };
  },
}));

describe("Dropzone", () => {
  beforeEach(() => {
    capturedOptions = {};
    vi.clearAllMocks();
  });

  it("defaults to PDF-only accept when no accept prop given (AC2.2)", () => {
    render(<Dropzone onFiles={vi.fn()} />);
    expect(capturedOptions.accept).toEqual({ "application/pdf": [".pdf"] });
  });

  it("passes NOTEBOOK_ACCEPT through when provided (AC2.1)", () => {
    render(<Dropzone onFiles={vi.fn()} accept={NOTEBOOK_ACCEPT} />);
    expect(capturedOptions.accept).toEqual(NOTEBOOK_ACCEPT);
    expect(capturedOptions.accept).toHaveProperty(
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    );
    expect(capturedOptions.accept).toHaveProperty(
      "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    );
  });

  it("shows rejection toast with correct extensions when files rejected (AC2.3)", () => {
    render(<Dropzone onFiles={vi.fn()} accept={NOTEBOOK_ACCEPT} />);
    capturedOptions.onDrop?.([], [{ file: new File([], "bad.txt") }]);
    expect(vi.mocked(sonner.toast.error)).toHaveBeenCalledWith(
      expect.stringContaining(".pdf")
    );
    expect(vi.mocked(sonner.toast.error)).toHaveBeenCalledWith(
      expect.stringContaining(".docx")
    );
  });

  it("shows PDF-only rejection message when no accept prop (AC2.2 + AC2.3)", () => {
    render(<Dropzone onFiles={vi.fn()} />);
    capturedOptions.onDrop?.([], [{ file: new File([], "bad.txt") }]);
    expect(vi.mocked(sonner.toast.error)).toHaveBeenCalledWith(
      expect.stringContaining(".pdf")
    );
    expect(vi.mocked(sonner.toast.error)).not.toHaveBeenCalledWith(
      expect.stringContaining(".docx")
    );
  });

  it("calls onFiles with accepted files", () => {
    const onFiles = vi.fn();
    render(<Dropzone onFiles={onFiles} accept={NOTEBOOK_ACCEPT} />);
    const files = [new File(["content"], "doc.pdf", { type: "application/pdf" })];
    capturedOptions.onDrop?.(files, []);
    expect(onFiles).toHaveBeenCalledWith(files);
  });

  it("renders dropzone root element", () => {
    render(<Dropzone onFiles={vi.fn()} />);
    expect(screen.getByTestId("dropzone-root")).toBeInTheDocument();
  });
});
