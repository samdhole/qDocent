# NotebookLM-Style UI Overhaul — Design Plan

**Date:** 2026-05-08
**Slug:** `nb-ui`
**Status:** Approved for implementation

---

## Goal

Bring DocQuery's web UI from "demo harness" to "polished product" comparable to NotebookLM. The current UI uses unstyled Tailwind primitives, has no real conversation continuity, no streaming, no source-panel deep linking. This overhaul delivers shadcn/ui visual polish, multi-turn conversation, token-streaming responses, suggested questions, drag-drop ingest, and a split-pane source viewer with citation highlights.

## Why now

- Backend RAG and ingestion are stable (239 tests green, citation round-trip working).
- The single biggest gap between DocQuery and NotebookLM is UI polish + the source side panel — not retrieval quality.
- Product-storyline: the demo's value is "trust the answer" → highlights on source PDF directly visualize that trust.

## Non-goals

- Auth / multi-user state (single-user local demo only).
- Cloud hosting / production infra.
- Theme switcher (dark mode out of scope; Tailwind v4 dark theme is wired but not surfaced as toggle).
- Migration to a different framework (stays on Next.js 16 App Router + React 19).
- **Full React component test infra.** This overhaul does NOT add `@testing-library/react` + jsdom + MSW. New frontend behavior (hooks, queue state machine, stream parsing) is verified manually per phase via the human test plan. We DO add minimal `vitest` (node mode only) for testing pure helper functions like `bboxConversion.ts` — that's a one-time 5-minute setup, not a full test pyramid. If full component testing becomes a priority, it's a separate phase.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ apps/web (Next.js 16 + React 19 + Tailwind v4 + shadcn/ui)   │
│                                                              │
│  AppShell (sidebar nav + main pane)                          │
│  ├── /ask     → ConversationView + SourcePanel (split)       │
│  ├── /documents → DropzoneUpload + DocumentsList             │
│  ├── /workflows → WorkflowRunner                             │
│  ├── /evals    → EvalReport                                  │
│  └── /reports  → ReportsList                                 │
└──────────────────────────────────────────────────────────────┘
           │ HTTP + SSE
           ▼
┌──────────────────────────────────────────────────────────────┐
│ apps/api (FastAPI)                                           │
│  POST /conversations             → create R2R conversation   │
│  POST /conversations/{id}/messages (streaming SSE)           │
│  GET  /documents/{id}/chunks      → bbox lookup for panel    │
│  GET  /documents/{id}/source      → PDF bytes (existing)     │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ R2R 3.6.6 (client.retrieval.agent + client.conversations)    │
└──────────────────────────────────────────────────────────────┘
```

### Key tech decisions

| Decision | Choice | Rationale |
|---|---|---|
| Component library | **shadcn/ui** (CLI 4.7.0) | Native Tailwind v4 support, copy-not-import, owns its code |
| Markdown rendering | **react-markdown + remark-gfm** | De-facto standard, supports GFM tables/lists in answers |
| Toast notifications | **sonner** (shadcn-bundled) | Built-in to shadcn, accessible |
| PDF viewer | **react-pdf** (pdfjs-dist) | Most mature React PDF renderer; supports page-level rendering + overlay |
| Streaming | **Server-Sent Events** (native EventSource on client) | Simpler than WebSockets; R2R already returns Generator |
| Conversation API | **R2R `client.retrieval.agent` + `client.conversations`** | The only R2R path that supports `conversation_id` |
| Drag-drop | **react-dropzone** | Industry standard, accessible, 5kb |

### What changes vs what stays

**Stays:** Ingestion pipeline, R2R integration for retrieval, citation header round-trip, document store, figure store, all 239 tests.

**Changes:**
- Frontend pages all migrate to shadcn/ui components.
- `apps/api/services/r2r_client.py` gains an `agent_query` function alongside `rag_query` (rag_query stays for non-conversational paths — RAGAS evaluation, smoke script).
- New `apps/api/routes/conversations.py` route owning POST /conversations + streaming POST /conversations/{id}/messages.
- New `apps/api/routes/documents.py:GET /documents/{id}/chunks` returning bbox metadata for source-panel highlights.
- Ingestion stores `data/documents/<doc_id>/chunks.json` so the chunks API can read bbox without a R2R call.

---

## Acceptance Criteria

### nb-ui.AC1: shadcn/ui foundation present

- **nb-ui.AC1.1 Success:** `apps/web/components.json` exists with Tailwind v4 config; `apps/web/components/ui/*.tsx` contains at minimum: button, card, input, textarea, scroll-area, sheet, tabs, dialog, sonner, separator, badge, skeleton.
- **nb-ui.AC1.2 Success:** `apps/web/lib/utils.ts` exports `cn` helper consumed by all ui components.
- **nb-ui.AC1.3 Success:** `npm run build` succeeds; `npm run lint` passes; existing pages still render unchanged after dependency install (no visual regression yet — that's Phase 2).

### nb-ui.AC2: Layout shell and migrated pages

- **nb-ui.AC2.1 Success:** A persistent left sidebar (`apps/web/components/AppSidebar.tsx`) renders on every route except `/`; navigation items: Ask, Documents, Workflows, Evaluations.
- **nb-ui.AC2.2 Success:** All pages (`/ask`, `/documents`, `/workflows`, `/evals`) render via shadcn Card/Button/Input components — no raw `<input className="border rounded">` remains.
- **nb-ui.AC2.3 Success:** Answer text in `AnswerCard` renders as Markdown (lists, bold, code blocks render correctly).
- **nb-ui.AC2.4 Failure mode:** A markdown injection attempt (e.g., `<script>` in answer) renders as plain text, not executes — react-markdown sanitizes by default.

### nb-ui.AC3: Multi-turn conversation context

- **nb-ui.AC3.1 Success:** A user submits Q1 ("What is the refund policy?"), receives an answer, then submits Q2 ("How long do I have?"); Q2's answer references the refund policy without the user re-stating it.
- **nb-ui.AC3.2 Success:** A new conversation can be started via a "New Conversation" button; this clears the thread state and creates a fresh `conversation_id`.
- **nb-ui.AC3.3 Success:** Each message in the thread shows its citations independently; older messages do not lose their citations when a new message is added.
- **nb-ui.AC3.4 Failure mode:** If R2R is down when starting a conversation, the UI shows an error toast and does not enter a half-broken state.

### nb-ui.AC4: Streaming response rendering

- **nb-ui.AC4.1 Success:** When a user submits a question, answer tokens appear progressively (not all at once). First token visible within ~2s of submission.
- **nb-ui.AC4.2 Success:** While streaming, a "Searching documents…" → "Generating answer…" status indicator updates as R2R emits search/citation/generation events.
- **nb-ui.AC4.3 Success:** Citations and figures appear after the answer completes (rendered from the final SSE event).
- **nb-ui.AC4.4 Failure mode:** A network drop mid-stream surfaces an error and leaves the partial answer visible (not blanked).

### nb-ui.AC5: Suggested questions + empty states

- **nb-ui.AC5.1 Success:** When the conversation is empty (zero messages), the Ask page shows 3-6 suggested-question chips. Clicking a chip submits it as a message.
- **nb-ui.AC5.2 Success:** Suggestions are derived from a small static seed list AND the filenames of currently-ingested documents (e.g., "Summarize <filename>"). Static seeds present even when zero docs ingested.
- **nb-ui.AC5.3 Success:** `/documents` empty state directs users to upload; `/evals` empty state directs to `make eval`.

### nb-ui.AC6: Drag-and-drop upload

- **nb-ui.AC6.1 Success:** A user drags one or more PDFs onto the Documents page; each file enters a "queued" → "uploading" → "completed"/"failed" lifecycle visible per-file.
- **nb-ui.AC6.2 Success:** Multi-file: dropping 3 PDFs at once enqueues all 3; uploads run sequentially (one POST /ingest/jobs at a time).
- **nb-ui.AC6.3 Success:** A non-PDF file is rejected client-side with a toast "Only PDFs are accepted"; no upload request is fired.
- **nb-ui.AC6.4 Success:** Completion toast (sonner) fires for each finished file; failure toast surfaces the error message from the API.

### nb-ui.AC7: Source side panel + citation highlights

- **nb-ui.AC7.1 Success:** Clicking a citation card on the Ask page opens a right-side panel rendering the source PDF at the cited page.
- **nb-ui.AC7.2 Success:** A semi-transparent rectangle highlights the cited chunk's bounding box on the page (using bbox from `data/documents/<doc_id>/chunks.json`).
- **nb-ui.AC7.3 Success:** Multi-page citations (`page_start ≠ page_end`) start at `page_start` with a "Pages X–Y" indicator and prev/next page navigation works.
- **nb-ui.AC7.4 Success:** Closing the panel via X or backdrop click returns to single-pane view.
- **nb-ui.AC7.5 Failure mode:** When `chunks.json` is missing for an old document (pre-overhaul ingest), the panel still opens to the right page but shows no highlight overlay; no crash.

---

## Phase Breakdown

| Phase | Scope | ACs | Type |
|-------|-------|-----|------|
| 1 | shadcn/ui foundation install | nb-ui.AC1 | Infrastructure |
| 2 | Layout shell + migrate all pages to shadcn + markdown answers | nb-ui.AC2 | Functionality |
| 3 | Conversation history (R2R `agent` switch + new routes + thread UI) | nb-ui.AC3 | Functionality |
| 4 | Streaming responses (SSE backend + frontend consumer) | nb-ui.AC4 | Functionality |
| 5 | Suggested questions + empty states | nb-ui.AC5 | Functionality |
| 6 | Drag-drop upload + multi-file queue + sonner toasts | nb-ui.AC6 | Functionality |
| 7 | Source side panel + citation highlights (chunks.json + react-pdf) | nb-ui.AC7 | Functionality |

Phase 1 is purely infrastructure (verified by build/lint succeeding). Phases 2–7 are all functionality phases with tests gated to specific ACs.

## Dependencies between phases

- **Phase 2** depends on Phase 1 (uses shadcn components).
- **Phase 3** is independent of Phase 1/2 visually but needs an answer renderer — easier after Phase 2.
- **Phase 4** depends on Phase 3 (streams via the same `agent` route created in Phase 3).
- **Phase 5** depends on Phase 2 (uses Card/Button).
- **Phase 6** depends on Phase 2 (uses Card + sonner).
- **Phase 7** depends on Phase 2 (uses Sheet + Card) AND requires `chunks.json` ingest persistence — its first task adds that.

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| `client.retrieval.agent` returns different citation shape than `rag` | Medium | Phase 3 task 1 is a spike: dump raw response shape with a real query, before writing transform code |
| react-pdf bundle size bloats first-load JS | Low | Lazy-load react-pdf only on `/ask` route via `next/dynamic({ ssr: false })` |
| SSE through Next.js dev proxy buffers tokens | Medium | Use direct `fetch` to API origin (same as existing `${API}/ask` pattern), not a Next.js API route |
| shadcn install rewrites `globals.css` and breaks existing styles | Low | Phase 1 task 1 backs up `globals.css` before init; verifies dev server boots after install |
| react-pdf worker file (pdf.worker.min.mjs) doesn't get bundled | Medium | Standard pattern is `pdfjs.GlobalWorkerOptions.workerSrc = …` referencing a CDN or local copy; documented in Phase 7 |

## Done when

- All 7 phases' ACs verified.
- 239+ existing tests still green.
- New tests added for: conversations route, streaming route, chunks route, citation panel state machine.
- `make web` boots clean, no console errors.
- A user can: ingest a PDF via drag-drop → ask a question → see streaming answer with markdown → click citation → see highlighted source → ask follow-up retaining context.
