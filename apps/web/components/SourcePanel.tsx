"use client";

import { useEffect, useMemo, useState } from "react";
import { Document, Page } from "react-pdf";
import "@/lib/pdfWorker"; // Side-effect import — sets the worker URL once.
// react-pdf internal path — verify this path exists after any react-pdf major-version upgrade
import "react-pdf/dist/esm/Page/TextLayer.css";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

import type { ChunkManifestEntry, ChunksResponse, SelectedCitation } from "@/lib/types";
import { bboxToCssBox, findOverlayChunk, isFullPageBbox } from "@/lib/bboxConversion";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Props = {
  citation: SelectedCitation | null;
  onClose: () => void;
};

export default function SourcePanel({ citation, onClose }: Props) {
  const [chunks, setChunks] = useState<ChunkManifestEntry[]>([]);
  const [pageNum, setPageNum] = useState<number | null>(null);
  const [pageDims, setPageDims] = useState<{ width: number; height: number; naturalWidth: number; naturalHeight: number } | null>(null);

  // Load chunks manifest and set initial page number when citation changes.
  useEffect(() => {
    if (!citation) {
      return;
    }

    // Set initial page number when citation changes
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPageNum(citation.pageStart);

    // Fetch chunks manifest
    const ctrl = new AbortController();
    fetch(`${API}/documents/${citation.documentId}/chunks`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : { chunks: [] }))
      .then((data: ChunksResponse) => {
        setChunks(data.chunks ?? []);
      })
      .catch(() => {
        setChunks([]);
      }); // AC7.5: missing/empty manifest → no overlay

    return () => ctrl.abort();
  }, [citation]);

  const overlayChunk = useMemo(
    () => findOverlayChunk(chunks, citation, pageNum),
    [chunks, citation, pageNum]
  );

  const overlayCss = useMemo(() => {
    if (!overlayChunk?.bbox || !pageDims) return null;
    return bboxToCssBox(overlayChunk.bbox, {
      pageWidthPx: pageDims.width,
      pageHeightPx: pageDims.height,
      naturalWidthPt: pageDims.naturalWidth,
      naturalHeightPt: pageDims.naturalHeight,
    });
  }, [overlayChunk, pageDims]);

  const isFullPage = useMemo(() => {
    if (!overlayChunk?.bbox || !pageDims) return false;
    return isFullPageBbox(overlayChunk.bbox, pageDims.naturalWidth, pageDims.naturalHeight);
  }, [overlayChunk, pageDims]);

  const open = citation !== null;

  function handlePageLoadSuccess(page: { width: number; height: number; originalWidth: number; originalHeight: number }) {
    if (!page.originalWidth || !page.originalHeight) return;
    setPageDims({
      width: page.width,
      height: page.height,
      naturalWidth: page.originalWidth,
      naturalHeight: page.originalHeight,
    });
  }

  function handlePrevPage() {
    if (!citation || pageNum == null) return;
    if (pageNum > citation.pageStart) setPageNum(pageNum - 1);
  }
  function handleNextPage() {
    if (!citation || pageNum == null) return;
    const end = citation.pageEnd ?? citation.pageStart;
    if (pageNum < end) setPageNum(pageNum + 1);
  }

  if (!citation) return null;

  const pageRange =
    citation.pageEnd && citation.pageEnd !== citation.pageStart
      ? `Pages ${citation.pageStart}–${citation.pageEnd}`
      : `Page ${citation.pageStart}`;

  const footerPage = pageNum ?? citation.pageStart;
  const citedEnd = citation.pageEnd ?? citation.pageStart;
  const footerLabel = citedEnd !== citation.pageStart
    ? `Page ${footerPage} · cited pp.${citation.pageStart}–${citedEnd}`
    : `Page ${footerPage}`;

  return (
    <Sheet open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <SheetContent side="right" className="w-full sm:w-[640px] sm:max-w-[640px] p-0 flex flex-col">
        <SheetHeader className="px-4 py-3 border-b">
          <SheetTitle className="text-sm font-medium flex items-center justify-between">
            <span className="truncate">{citation.documentName}</span>
            <Button variant="ghost" size="icon" className="size-7" onClick={onClose}>
              <X className="size-4" />
              <span className="sr-only">Close</span>
            </Button>
          </SheetTitle>
          <SheetDescription className="sr-only">Source document viewer for {citation.documentName}</SheetDescription>
          <p className="text-xs text-muted-foreground">{pageRange}</p>
        </SheetHeader>

        <div className="flex-1 overflow-auto bg-muted/40 p-4">
          <div className="flex justify-center">
            <div className="relative inline-block">
              <Document
                file={`${API}/documents/${citation.documentId}/source`}
                loading={<p className="text-sm text-muted-foreground">Loading PDF…</p>}
                error={<p className="text-sm text-destructive">Could not load PDF.</p>}
              >
                {pageNum != null && (
                  <Page
                    pageNumber={pageNum}
                    width={580}
                    onLoadSuccess={handlePageLoadSuccess}
                    renderAnnotationLayer={false}
                    renderTextLayer={true}
                  />
                )}
              </Document>
              {overlayCss && !isFullPage && (
                <div
                  className="absolute pointer-events-none border-2 border-yellow-400 bg-yellow-300/50 z-10"
                  style={{
                    left: overlayCss.left,
                    top: overlayCss.top,
                    width: overlayCss.width,
                    height: overlayCss.height,
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Empty text_preview → hide the strip; no point quoting nothing */}
        {overlayChunk?.text_preview && (
          <div className="px-4 py-3 border-t bg-muted/20">
            <p className="text-xs font-medium text-muted-foreground mb-1">Cited passage</p>
            <p className="text-xs leading-relaxed line-clamp-4 text-foreground">
              {overlayChunk.text_preview}
            </p>
          </div>
        )}

        <div className="px-4 py-2 border-t flex items-center justify-between bg-background">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevPage}
            disabled={pageNum == null || pageNum <= citation.pageStart}
          >
            <ChevronLeft className="size-4 mr-1" /> Previous
          </Button>
          <span className="text-xs text-muted-foreground">
            {footerLabel}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNextPage}
            disabled={pageNum == null || pageNum >= (citation.pageEnd ?? citation.pageStart)}
          >
            Next <ChevronRight className="size-4 ml-1" />
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
