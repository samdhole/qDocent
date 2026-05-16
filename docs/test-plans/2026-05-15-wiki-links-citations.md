# Human Test Plan — Wiki Inter-Page Links & Source Citations

Generated: 2026-05-15

## Prerequisites
- `make r2r`, `make api`, `make web` all running
- A notebook with at least 2 ingested PDFs (use `make demo-setup` or upload via `/documents`)
- `pytest tests/test_wiki_prompts.py tests/test_wiki_generator.py -v` passing
- `cd apps/web && npx vitest run components/__tests__/WikiPage.test.tsx` passing

---

## Phase 1: Wiki generation with cross-references

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `http://localhost:3000/notebooks/<id>`, click "Generate Wiki" | Job progress shows `pages_done/pages_total`; completes within ~1–2 min |
| 2 | Navigate to `/notebooks/<id>/wiki/<first-slug>` | Page renders with title + markdown body |
| 3 | Scroll body looking for inline links to sibling wiki pages | At least one inline link to another `/notebooks/<id>/wiki/<other-slug>` |
| 4 | Verify "Closely related pages" callout (if `related_slugs` was emitted by the structure prompt) | Shows links to related pages distinct from the inline cross-reference index |

---

## Phase 2: AC4.1 — Server-side docName resolution (manual)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open browser devtools Network tab; load `/notebooks/<id>/wiki/<slug>` | Server-rendered HTML already contains the resolved filename in the source-doc badge (no client-side fetch for doc names) |
| 2 | View page source (Ctrl+U) | Badge text shows the real `report.pdf` style filename, not a short ID |

---

## Phase 3: AC5 — Source doc badges

| Step | Action | Expected |
|------|--------|----------|
| 1 | On a wiki page with source docs, locate the "SOURCE DOCUMENTS" section at the bottom | One badge per source doc; each shows the filename with an external-link icon |
| 2 | Hover the badge | Cursor becomes a pointer; underline/affordance suggests clickability |
| 3 | Click the badge | Opens new tab to `${API}/documents/<id>/source` (the PDF) |
| 4 | Visit a wiki page generated from no sources | "SOURCE DOCUMENTS" section is not rendered |

---

## Phase 4: AC6 — Inter-wiki link navigation

| Step | Action | Expected |
|------|--------|----------|
| 1 | On a wiki page, click an inline link to another wiki page | URL updates and target page renders WITHOUT a full browser reload (Next.js client transition — favicon doesn't blink, no white flash) |
| 2 | In the same wiki body, click an external `https://` link | Opens in a NEW tab with `rel=noopener` semantics |
| 3 | Browser Back button after the inter-wiki nav | Returns to previous wiki page, scroll position preserved |

---

## End-to-End: New user wiki exploration

Purpose: Validates the full feature delivers a navigable, sourced wiki.

1. Fresh notebook, ingest 3 PDFs covering related topics
2. Generate wiki, wait for completion
3. From Overview page, follow a cross-reference link to another page
4. From that page, click a source-doc badge — PDF opens in new tab at the correct document
5. Use browser back to return; click an external citation/URL — opens in new tab
6. Confirm no console errors throughout

---

## Human Verification Required

| Criterion | Why Manual | Steps |
|-----------|------------|-------|
| AC4.1 | Server component data-fetch behavior; cannot be asserted by unit test of WikiPage props | Phase 2 above (view source / Network tab) |
| LLM quality | Cross-reference relevance is a judgement call | Spot-check 3 pages: do inline links make semantic sense, or are they decorative? |
| No reload UX | Visual smoothness is human-perceptible | Phase 4 step 1 — watch for white flash |

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1–1.3 | `test_wiki_prompts.py` (cross_reference_index, related_pages_callout) | Phase 1 step 3–4 |
| AC2.1–2.3 | `test_wiki_generator.py::test_generate_page_content_forwards_all_pages_and_notebook_id` | Phase 1 step 1 |
| AC3.1–3.3 | `test_wiki_prompts.py` (3 cases incl. empty + no-arg) | — |
| AC4.1 | (none — by design) | Phase 2 |
| AC4.3–4.4 | `WikiPage.test.tsx` (badge render + fallback) | Phase 3 step 1 |
| AC5.1, 5.3 | `WikiPage.test.tsx` (clickable + hidden when empty) | Phase 3 steps 2–4 |
| AC6.1–6.3 | `WikiPage.test.tsx` (internal Link, external new tab) | Phase 4 |
| AC7.1–7.4 | `WikiPage.test.tsx` suite | — |
