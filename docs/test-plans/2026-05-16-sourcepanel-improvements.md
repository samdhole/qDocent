# Human Test Plan: SourcePanel Improvements

**Branch:** docker-windows-reliability  
**Plan:** docs/implementation-plans/2026-05-16-sourcepanel-improvements/  
**Date:** 2026-05-16

---

## Prerequisites

- Local stack running: `make r2r`, `make api`, `make web` in separate terminals (R2R on :7272, API on :8000, web on :3000)
- At least one ingested PDF (any PDF — the pipeline produces single-page chunks by design, so multi-page citations will not appear in the browser regardless of corpus)
- Vitest gate passing: `cd apps/web && npx vitest run components/__tests__/SourcePanel.test.tsx` reports `16 passed`
- A modern browser (Chrome/Firefox/Safari) — text-layer requires real canvas

---

## Phase 1: Text Layer Enabled (AC1.1, AC1.2)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to `http://localhost:3000/ask` (or open any notebook conversation with at least one prior answer with citations). If empty, ask a question that produces a cited answer such as "Summarize the key risks discussed". | Answer streams in with one or more `[N]` citation chips inline. |
| 2 | Click any citation chip `[N]` in the rendered answer. | Right-side `SourcePanel` Sheet slides in showing the PDF page. Loading spinner appears briefly. |
| 3 | Once the PDF page renders, click-drag across a line of body text inside the PDF viewer. | Native text selection highlight appears over the dragged glyphs (blue/system highlight). |
| 4 | With text still selected, press `Ctrl+C` (or `Cmd+C` on macOS), then paste into another application. | The exact text from the PDF appears in the destination, not garbled or empty. |
| 5 | Press `Ctrl+F` (or `Cmd+F`) inside the browser. Type a short word you can see on the rendered PDF page (e.g. "the"). | Browser find-in-page highlights the term within the PDF text layer (in addition to surrounding page text). |
| 6 | Observe the yellow bounding-box highlight (if the cited chunk is not full-page). | The yellow border + 50% semi-transparent yellow fill is **visible on top of** the PDF page (not hidden behind it). Text under the highlight is still legible through the translucent overlay. |
| 7 | Try clicking through to a different citation that lands on a non-cited region of a different page. | If the chunk's bbox is >= 90% of both page dimensions (full-page chunk), **no** yellow overlay is drawn — the page renders clean. The "Cited passage" text strip below the PDF still shows the chunk text if `text_preview` is non-empty. |

---

## Phase 2: Footer Format (AC2.1, AC2.2, AC2.3, AC2.4)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click a citation whose page range is a **single page** (e.g. cited page 5 only, `pageStart === pageEnd`). | SourcePanel opens. Footer (between Previous/Next buttons) reads exactly `Page 5`. No `·` middle-dot, no `cited pp.` suffix anywhere in the footer. |
| 2 | *(AC2.2 — automated test only)* Multi-page footer `Page N · cited pp.X–Y` cannot be triggered manually. The DocQuery pipeline always sets `page_start = page_end = current page` in `chunk_templates.py`, so every real citation is single-page. The `· cited pp.X–Y` suffix is covered by `SourcePanel.test.tsx:332` via a synthetic `pageStart:3, pageEnd:7` citation. No manual step needed. | N/A — see automated test. |
| 3 | *(Skipped — depends on step 2)* | N/A |
| 4 | *(Skipped — depends on step 2)* | N/A |
| 5 | *(Skipped — depends on step 2)* | N/A |
| 6 | Scan the entire footer area while interacting with several different citations (single + multi). | At no point does the legacy `Page N of M` format appear. The format is always one of: `Page N` or `Page N · cited pp.X–Y`. |

---

## End-to-End: Cited passage with text-layer copy

Purpose: validates AC1 (text layer) + AC2 (footer format) together on a single realistic flow. Multi-page citations do not occur with this corpus (pipeline is page-per-chunk by design), so the end-to-end uses a single-page citation.

1. Open `/ask` and submit a question that produces a cited answer (e.g. "What are the key findings?").
2. Click any `[N]` citation chip. SourcePanel opens.
3. Verify the document name in the header and the footer shows `Page N` (single-page format).
4. Click-drag-select a sentence inside the cited passage on the rendered PDF page. Copy with `Ctrl+C` and paste elsewhere.
5. Confirm the pasted text matches what is visually rendered on the page.
6. Click the **X** in the header. Sheet closes. Conversation view regains focus.

---

## Human Verification Required

| Criterion | Why Manual | Steps |
|-----------|------------|-------|
| AC1.1 (text layer enabled) | react-pdf's text layer requires the real browser canvas; jsdom stubs out PDF rendering so a unit test would only assert the prop, not the user-visible selectability. | Phase 1 steps 3–5 above. |
| AC1.2 (overlay still on top) | z-stacking and translucent fill are pixel-level visual properties; no DOM-level assertion can confirm "the user can still read text under the highlight." | Phase 1 step 6 above. |

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 (text layer enabled) | — (manual only) | Phase 1, steps 3–5 |
| AC1.2 (overlay still on top) | — (manual only) | Phase 1, step 6 |
| AC1.3 (regression — tests still pass) | `SourcePanel.test.tsx` — all 16 tests pass | — (covered by CI) |
| AC2.1 (single-page footer "Page N") | `SourcePanel.test.tsx:354` | Phase 2, step 1 |
| AC2.2 (multi-page footer "Page N · cited pp.X–Y") | `SourcePanel.test.tsx:332` | **Automated only** — pipeline produces single-page chunks by design; no manual step possible with this corpus |
| AC2.3 (no range suffix when single-page) | `SourcePanel.test.tsx:372` (negative assertion) | Phase 2, step 1 |
| AC2.4 (no stale assertions on old format) | All 16 tests pass, no `N of M` references remain | Phase 2, step 6 |
