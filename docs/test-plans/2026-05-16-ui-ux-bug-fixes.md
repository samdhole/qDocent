# Human Test Plan: UI/UX Bug Fixes (2026-05-16)

**Plan:** `docs/implementation-plans/2026-05-16-ui-ux-bug-fixes/`
**Coverage:** 11/11 automated AC criteria pass. Manual verification required for 9 AC criteria (rendering, timing, layout, full-router behaviour).

---

## Prerequisites

- Project running locally: `make r2r` (port 7272), `make api` (port 8000), `make web` (port 3000).
- At least one ingested PDF document (e.g. run `make demo-setup` or upload a PDF via `/documents`).
- All automated tests passing: `cd apps/web && npx vitest run` (124 tests green).
- Browser open at `http://localhost:3000`.

---

## Phase 1: Citation rendering (AC1, AC2)

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Navigate to `/ask`. Ask a question that should produce ≥4 citations from a single document (e.g. "Summarize the entire 10-K"). | Answer renders with inline `[N]` badges. |
| 1.2 | Inspect the answer markdown for any grouped citations like `[2, 4, 5]`. | Each number appears as a separate badge — not one combined badge "[2, 4, 5]". |
| 1.3 | Hover over an active blue `[N]` badge for ~200 ms without moving. | A HoverCard tooltip appears showing the chunk text excerpt, `p.{N} · {document_name}` line. |
| 1.4 | Move pointer away from the badge. | Tooltip disappears within ~300 ms. |
| 1.5 | Click the same `[N]` badge. | SourcePanel opens (sheet slides in from the right). Tooltip disappears as the panel opens. |
| 1.6 | Find a citation that is greyed out (no `document_id` / `page`). | Badge has muted background and is not clickable; hovering shows no tooltip. |
| 1.7 | Look for any out-of-bounds `[99]` style reference. | Renders greyed `<span>`, not a button; no tooltip; no click effect. |

---

## Phase 2: SourcePanel highlight + text strip (AC3)

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | From Phase 1, the SourcePanel is open at the cited page. Look for a yellow translucent box. | If the chunk has a precise bbox, a yellow rectangle is visible (≥50% opacity fill, border) around the cited text. |
| 2.2 | Below the rendered PDF page, locate the "Cited passage" strip. | Strip renders verbatim chunk text, up to 4 lines. |
| 2.3 | Click a citation that references a full-page text chunk. | No yellow overlay is drawn, but the "Cited passage" text strip is still visible. |
| 2.4 | Close the SourcePanel and click another citation. | Panel re-opens at the new page with correct highlight/strip. |

---

## Phase 3: NotebookCard navigation (AC4)

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | Navigate to `/notebooks`. Click anywhere on the body of a NotebookCard (title or description area — not action buttons). | Browser navigates to `/notebooks/{id}`. |
| 3.2 | Back to `/notebooks`. Click the trash icon on a card. | Card switches to confirm state. No navigation occurs. |
| 3.3 | Click "Cancel". | Confirm state reverts. URL still `/notebooks`. No navigation. |
| 3.4 | Click trash again, then "Delete". | Delete fires; card disappears. URL still `/notebooks`. |
| 3.5 | Click the visible "Open" button. | Navigates to `/notebooks/{id}`. |
| 3.6 | Tab through the page with keyboard. | The invisible overlay link is not tab-reachable (`tabIndex={-1}`); the visible "Open" button is. |

---

## Phase 4: AnswerCard copy button (AC5)

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | Ask any question with a high-confidence answer. | Copy icon visible at far right of Answer header (ml-auto). |
| 4.2 | Click the copy icon. | Icon switches to checkmark briefly (~2 s), then reverts. Clipboard contains the answer text. |
| 4.3 | Ask a question with `needs_human_review: true`. | "Human review recommended" orange text AND the copy icon appear on the same row. |
| 4.4 | Click copy on the low-confidence answer. | Same checkmark feedback; clipboard contains the answer. |

---

## Phase 5: SuggestedQuestions formatting (AC6)

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | Navigate to `/ask` with a document that has a multi-word filename (e.g. `robinhood_10k_2024.pdf`). | Empty state renders suggestion chips. |
| 5.2 | Find a chip starting with "Summarize ". | Doc title has no underscores, no dashes, no `.pdf` extension — e.g. "Summarize robinhood 10k 2024". |
| 5.3 | If a document has a very long filename (>40 chars after extension strip), check its Summarize chip. | Title ends with `…` and total length ≤41 chars. No trailing space before `…`. |
| 5.4 | Click a Summarize chip. | Text fills the chat input and submits as a question. |

---

## Phase 6: /demo figure caption (AC7)

| Step | Action | Expected |
|------|--------|----------|
| 6.1 | Navigate to `/demo`. Scroll to the figure section. | A figure image is rendered with a caption. |
| 6.2 | Read the caption text. | Caption says "Figure extracted from the demo 10-K corpus." — no `make demo-setup`, no `<code>` element, no CLI instruction. |

---

## End-to-End: Citation drill-down flow

**Purpose:** Validate Phase 1–3 together — from streaming answer to highlighted source.

1. Navigate to `/ask` (or a notebook conversation at `/notebooks/{id}`).
2. Submit "What are the main risk factors?" — should retrieve multiple chunks.
3. While streaming, observe greyed `[N]` badges appearing inline.
4. Once streaming completes, badges turn blue and clickable.
5. Hover the first badge — tooltip shows chunk preview within ~150 ms.
6. Click the badge — SourcePanel opens at the correct PDF page.
7. Confirm the "Cited passage" strip matches the tooltip text from step 5.
8. If a precise bbox exists, yellow overlay is visible. If full-page text chunk, no overlay but strip is present.
9. Close the SourcePanel, click a different badge — panel re-opens at a different page.

---

## End-to-End: Whole-card navigation + delete flow

**Purpose:** Validate AC4.1 + AC4.2 don't conflict.

1. From `/notebooks`, create a throwaway notebook ("test card nav").
2. Click the card body (title or description). Confirm navigation to `/notebooks/{id}`.
3. Use browser back to return to `/notebooks`.
4. Click the trash icon — confirm state appears, URL unchanged.
5. Click "Cancel" — state reverts, URL unchanged.
6. Click trash again, then "Delete" — notebook removed, URL still `/notebooks`.

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 — comma-group `[2, 4, 5]` → 3 nodes | `remarkCitationBadges.test.ts` | Phase 1, step 1.2 |
| AC1.2 — single `[1]` → 1 node | `remarkCitationBadges.test.ts` | Phase 1, step 1.1 |
| AC1.3 — mixed groups → nodes in order | `remarkCitationBadges.test.ts` | Phase 1, step 1.2 |
| AC1.4 — groups in code block → no nodes | `remarkCitationBadges.test.ts` | n/a (developer-facing) |
| AC2.1 — hover 150 ms shows tooltip | n/a | Phase 1, steps 1.3–1.5 |
| AC2.2 — click opens SourcePanel, no dialog | `CitationBadge.test.tsx` | Phase 1, step 1.5 |
| AC2.3 — no source → disabled button, no HoverCard | `CitationBadge.test.tsx` | Phase 1, step 1.6 |
| AC2.4 — out-of-bounds → span fallback | `CitationBadge.test.tsx` | Phase 1, step 1.7 |
| AC3.1 — precise bbox overlay ≥50% opacity | n/a | Phase 2, step 2.1 |
| AC3.2 — full-page bbox → no overlay | `bboxConversion.test.ts` | Phase 2, step 2.3 |
| AC3.3 — text strip present regardless of bbox type | n/a | Phase 2, step 2.2 |
| AC3.4 — `isFullPageBbox` ≥90% both axes → true | `bboxConversion.test.ts` | n/a |
| AC4.1 — whole card click navigates | n/a | Phase 3, steps 3.1, 3.5 |
| AC4.2 — action buttons don't navigate | n/a | Phase 3, steps 3.2–3.4 |
| AC5.1 — copy button always visible | n/a | Phase 4, steps 4.1–4.2 |
| AC5.2 — "Human review" label still present | n/a | Phase 4, step 4.3 |
| AC6.1 — extension stripped, separators normalized | `docTitleFormatter.test.ts` | Phase 5, step 5.2 |
| AC6.2 — truncated at 40 chars with `…` | `docTitleFormatter.test.ts` | Phase 5, step 5.3 |
| AC6.3 — Summarize chip uses formatted title | n/a | Phase 5, step 5.2 |
| AC7.1 — no CLI instruction in /demo caption | n/a (source grep confirms) | Phase 6, steps 6.1–6.2 |
