import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useBatchUpload } from "../useBatchUpload";

const mockFetch = vi.fn();
global.fetch = mockFetch;

function makeFile(name: string): File {
  return new File(["content"], name, { type: "application/pdf" });
}

describe("useBatchUpload", () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  it("starts in idle state with no items", () => {
    const { result } = renderHook(() => useBatchUpload());
    expect(result.current.batchStatus).toBe("idle");
    expect(result.current.items).toHaveLength(0);
    expect(result.current.total).toBe(0);
  });

  it("transitions to running then complete on success (AC1.4)", async () => {
    mockFetch.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => useBatchUpload());
    act(() => {
      result.current.start([makeFile("a.pdf"), makeFile("b.pdf")], "nb-1");
    });

    expect(result.current.batchStatus).toBe("running");
    expect(result.current.total).toBe(2);

    await waitFor(() => expect(result.current.batchStatus).toBe("complete"));
    expect(result.current.done).toBe(2);
    expect(result.current.failed).toBe(0);
  });

  it("marks failed items on non-ok response and exposes error (AC1.5)", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    mockFetch.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => useBatchUpload());
    act(() => {
      result.current.start(
        [makeFile("fail.pdf"), makeFile("ok.pdf")],
        "nb-1"
      );
    });

    await waitFor(() => expect(result.current.batchStatus).toBe("complete"));
    expect(result.current.failed).toBe(1);
    expect(result.current.done).toBe(1);

    const failedItem = result.current.items.find((i) => i.status === "failed");
    expect(failedItem).toBeDefined();
    expect(failedItem?.error).toMatch(/HTTP 500/);
  });

  it("caps concurrent uploads at 4 (AC1.6)", async () => {
    let maxConcurrent = 0;
    let current = 0;

    // Each mock fetch tracks concurrent count and resolves slowly
    mockFetch.mockImplementation(
      () =>
        new Promise<{ ok: boolean }>((resolve) => {
          current += 1;
          maxConcurrent = Math.max(maxConcurrent, current);
          setTimeout(() => {
            current -= 1;
            resolve({ ok: true });
          }, 10);
        })
    );

    const files = Array.from({ length: 8 }, (_, i) =>
      makeFile(`file${i}.pdf`)
    );
    const { result } = renderHook(() => useBatchUpload());

    act(() => {
      result.current.start(files, "nb-1");
    });

    await waitFor(() => expect(result.current.batchStatus).toBe("complete"), {
      timeout: 2000,
    });

    expect(maxConcurrent).toBeGreaterThan(1);
    expect(maxConcurrent).toBeLessThanOrEqual(4);
    expect(result.current.done).toBe(8);
  });

  it("respects custom concurrency option", async () => {
    let maxConcurrent = 0;
    let current = 0;

    mockFetch.mockImplementation(
      () =>
        new Promise<{ ok: boolean }>((resolve) => {
          current += 1;
          maxConcurrent = Math.max(maxConcurrent, current);
          setTimeout(() => {
            current -= 1;
            resolve({ ok: true });
          }, 10);
        })
    );

    const files = Array.from({ length: 6 }, (_, i) =>
      makeFile(`file${i}.pdf`)
    );
    const { result } = renderHook(() => useBatchUpload({ concurrency: 2 }));

    act(() => {
      result.current.start(files, "nb-1");
    });

    await waitFor(() => expect(result.current.batchStatus).toBe("complete"), {
      timeout: 2000,
    });

    expect(maxConcurrent).toBeLessThanOrEqual(2);
  });

  it("aborts in-flight requests on unmount", async () => {
    const resolveAll: Array<() => void> = [];
    let capturedSignal: AbortSignal | undefined;

    mockFetch.mockImplementation(
      (_url: string, options?: RequestInit) =>
        new Promise<{ ok: boolean }>((resolve) => {
          if (options?.signal) {
            capturedSignal = options.signal;
          }
          resolveAll.push(() => resolve({ ok: true }));
        })
    );

    const { result, unmount } = renderHook(() => useBatchUpload());
    act(() => {
      result.current.start([makeFile("a.pdf")], "nb-1");
    });

    expect(result.current.batchStatus).toBe("running");
    // Unmount should abort in-flight requests
    unmount();
    resolveAll.forEach((r) => r());

    // Verify the AbortController was triggered
    expect(capturedSignal?.aborted).toBe(true);
  });
});
