# Human Test Plan: cite-and-scope

**Plan:** `docs/implementation-plans/2026-05-09-cite-and-scope/`
**Coverage:** 19/19 ACs automated; 5 ACs require manual browser verification.
**Last verified:** 2026-05-09

---

## Prerequisites

- `make r2r` (terminal 1, port 7272), `make api` (terminal 2, port 8000), `make web` (terminal 3, port 3000)
- At least 3 ingested documents with retrievable content. If empty: `make ingest` to load samples.
- Open `http://localhost:3000/ask` in Chrome with DevTools available (Network + device emulation).
- Known-good baseline: `.venv/Scripts/python.exe -m pytest tests/ -v` and `cd apps/web && npx vitest run` both green.

---

## Phase 1: AC1.1 / AC1.2 — Hover-preview citations (real browser)

| Step | Action | Expected |
|------|--------|----------|
| 1 | On `/ask`, ask "What is the refund policy?" (or any question that returns at least one cited answer). Wait for streaming to finish. | Answer renders with at least one inline blue `[1]` chip in prose. |
| 2 | Move mouse over the `[1]` chip and hold still. | Within ~200 ms (Radix `openDelay` ~150 ms), a HoverCard pops open. **AC1.1** |
| 3 | Read the HoverCard content. | Shows: (a) verbatim chunk text matching `retrievedContexts[0].text`, (b) source filename (e.g. `policy.pdf`), (c) footer `p.{page}` (e.g. `p.1`). **AC1.2** |
| 4 | Move mouse off the chip. | HoverCard closes; no flicker. |
| 5 | Hover a `[2]` chip if available. | HoverCard reveals the chunk for index 2; content differs from `[1]`. |

---

## Phase 2: AC1.5 — Touch-tap on mobile

| Step | Action | Expected |
|------|--------|----------|
| 1 | DevTools → Toggle device toolbar (Ctrl+Shift+M) → choose iPhone or Pixel preset. Reload `/ask`. | Mobile viewport renders; sidebar is hidden. |
| 2 | Ask a question that produces citations. Wait for response. | Inline `[N]` chips visible in answer. |
| 3 | Single-tap a `[1]` chip with mouse (simulating touch). | SourcePanel opens directly to the cited page; **no HoverCard appears mid-tap**. |
| 4 | Close SourcePanel (X or escape). | Panel closes; UI returns to chat. |

---

## Phase 3: Inline chips integration + AnswerCard panel refactor (AC2.5, AC2.6)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask a question that returns multiple citations. | Answer text contains visible inline `[1]`, `[2]`, ... chips inline (not just at the end). |
| 2 | Inspect the Citations panel below the answer. | Panel shows `[1]`, `[2]`, ... badge buttons (not the old `<ul>/<li>` plain list). |
| 3 | Click `[2]` in the inline answer prose. | SourcePanel opens at the page cited by index 2 (cross-check page footer in HoverCard from Phase 1 step 5). |
| 4 | Close, then click `[2]` in the Citations panel below. | SourcePanel opens to the same page. |
| 5 | If the answer contains a fenced code block with `[1]` inside, verify chip is **not** rendered inside the code block (text remains literal `[1]`). | Confirms `remarkCitationBadges` ignores `code`/`inlineCode` (AC2.6 integration). |

---

## Phase 4: AC3.1 (UI) — QueryModeToggle persistence

| Step | Action | Expected |
|------|--------|----------|
| 1 | On `/ask` chat footer, locate the `Docs | General` segmented control. | Both segments visible; `Docs` selected by default on first load. |
| 2 | Click `General`. | `General` highlights; `Docs` unhighlights. |
| 3 | Hard reload (Ctrl+F5). | After hydration, `General` is still selected. |
| 4 | DevTools → Application → Local Storage → `http://localhost:3000` → confirm `docquery.queryMode = "general"`. | Key/value present and correct. |
| 5 | Click `Docs`, reload again. | `Docs` selected; localStorage value `documents`. |

---

## Phase 5: AC3.6 — Strict not-found amber CTA

| Step | Action | Expected |
|------|--------|----------|
| 1 | Set toggle to `Docs`. Ask a question clearly not in your corpus (e.g. "What is the capital of Saturn?"). | Answer renders as `"I couldn't find this in your documents."` |
| 2 | Inspect the AnswerCard. | An amber banner appears with copy like "Switch to General knowledge to broaden" and a clickable CTA. |
| 3 | Click the CTA. | `queryMode` flips to `general` (toggle visibly switches); subsequent ask proceeds without the not-found substitution. |

---

## Phase 6: AC4.3 (E2E) — Document-scoped POST body

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open DevTools → Network → filter by "stream". | Empty list initially. |
| 2 | Click in the chat input and type `#`. | Picker listbox opens listing up to 8 ingested documents. |
| 3 | Type `#rep` (or any substring matching one of your filenames). | Picker filters to matching docs (case-insensitive). |
| 4 | Use ArrowDown/Up to highlight a doc, press Enter. | Chip appears next to the input; the `#token` is removed from input text. |
| 5 | Type a question and hit Enter. | A request fires to `/conversations/{id}/messages/stream`. |
| 6 | In DevTools Network, click the new request → Payload tab. | POST body JSON contains `"document_id": "<the chip's document_id>"`. |
| 7 | After the response completes, inspect the chip. | Chip is gone (per-message scope, AC4.4 integration). |
| 8 | Send another message without selecting a doc. | New POST body has no `document_id` field. |

---

## End-to-End: Full citation deep-link round trip

Purpose: validates AC1.1 + AC1.2 + AC1.3 + AC2.5 + Phase 3 integration end-to-end against a real R2R retrieval.

1. Reset toggle to `Docs`. Type `#refund` (or appropriate filename), select via Enter, type "What is the refund period?", submit.
2. Watch streaming partial render. While streaming, confirm in-flight `[N]` markers appear as greyed badges (not yet clickable).
3. After completion, hover `[1]` — HoverCard shows chunk text + page (Phase 1).
4. Click `[1]` — SourcePanel opens at the cited page; yellow bbox highlights the chunk on the rendered PDF.
5. Close panel, click the matching `[1]` in the Citations panel below — same SourcePanel opens at the same page.
6. DevTools Network → confirm POST body for the original request had `"document_id"` set, `"doc_only": true`.
7. Ask follow-up "And the return shipping?" without re-attaching. POST body should still have `doc_only: true` but **no** `document_id` (chip cleared on submit).

---

## Human Verification Required

| Criterion | Why Manual | Steps |
|-----------|------------|-------|
| AC1.1 | jsdom does not fire real pointer/hover events | Phase 1 steps 2–5 |
| AC1.2 | Same as AC1.1 — visual content match | Phase 1 step 3 |
| AC1.5 | Real touch / device emulation required | Phase 2 |
| AC3.1 (UI) | Hook persistence is automated; wired-up segmented control + reload is visual | Phase 4 |
| AC3.6 | No automated AnswerCard banner test | Phase 5 |
| AC4.3 (E2E) | Backend filter is unit-tested; UI→POST integration is manual | Phase 6 |
| Inline chips integration | Plugin unit-tested; `react-markdown` + `cite-ref` mapping is manual | Phase 3 |
| AnswerCard panel refactor | Component tests cover badge in isolation; AnswerCard integration is manual | Phase 3 steps 2, 4 |

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 | — | Phase 1 step 2 |
| AC1.2 | — | Phase 1 step 3 |
| AC1.3 | `CitationBadge.test.tsx` (click + Enter + Space) | Phase 3 steps 3–4 (integration) |
| AC1.4 | `CitationBadge.test.tsx` (out-of-bounds) | — |
| AC1.5 | — | Phase 2 step 3 |
| AC2.1 | `test_citation_marker_rewriter.py::test_ac2_1` | — |
| AC2.2 | `test_citation_marker_rewriter.py::test_ac2_2` | — |
| AC2.3 | `test_citation_marker_rewriter.py::test_ac2_3` | — |
| AC2.4 | `test_citation_marker_rewriter.py::test_ac2_4` | — |
| AC2.5 | `remarkCitationBadges.test.ts` (replacement) | Phase 3 step 1 (integration) |
| AC2.6 | `remarkCitationBadges.test.ts` (code exclusion) | Phase 3 step 5 |
| AC3.1 | `useQueryMode.test.ts` | Phase 4 (UI rendering + reload) |
| AC3.2 | `test_r2r_agent.py::TestDocOnly::test_ac3_2_*` (sync + stream) | — |
| AC3.3 | `test_r2r_agent.py::TestDocOnly::test_ac3_3_doc_only_low_score_chunk` | — |
| AC3.4 | `test_r2r_agent.py::TestDocOnly::test_ac3_4_*` (sync + stream) | — |
| AC3.5 | `test_r2r_agent.py::TestDocOnly::test_ac3_5_doc_only_false_empty_retrieval` | — |
| AC3.6 | — | Phase 5 |
| AC4.1 | `ChatInput.test.tsx` (substring filter) | Phase 6 step 3 |
| AC4.2 | `ChatInput.test.tsx` (arrow + Enter) | Phase 6 step 4 |
| AC4.3 | `test_r2r_agent.py::TestDocumentFilter::test_ac4_3_*` (sync + stream) | Phase 6 steps 5–6 |
| AC4.4 | `ChatInput.test.tsx` (chip cleared post-submit) | Phase 6 step 7 |
| AC4.5 | `ChatInput.test.tsx` (Escape + Tab) | — |
| AC4.6 | `ChatInput.test.tsx` (empty docs) | — |
| AC4.7 | `test_r2r_agent.py::TestDocumentFilter::test_ac4_7_*` (None + empty list) | — |
