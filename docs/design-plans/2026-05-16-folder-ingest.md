# Folder Ingestion & Multi-Format Upload Design

## Summary

This design adds three related upload enhancements to the DocQuery web UI, all frontend-only. The backend already exposes every required endpoint — no API changes are needed.

The centerpiece is a folder ingestion wizard: a 4-step Dialog that lets a user point at a local folder, create a notebook, and watch all supported documents (.pdf, .docx, .pptx) upload in parallel batches of four. A new `useBatchUpload` hook owns the concurrency logic and per-file status tracking. On completion the wizard offers to kick off wiki generation and navigate directly into the notebook.

The two supporting features are smaller: the existing `Dropzone` component is made configurable via an `accept` prop (currently hardwired to PDF) so the notebook detail page can accept all three document types, and a URL ingest input is added to the notebook detail page so users can pull in web pages alongside local files. All three features are delivered in four sequential phases, each with a self-contained "done when" definition mapping to numbered acceptance criteria.

## Definition of Done

1. User can pick a local folder from the `/notebooks` list page → a wizard creates a notebook → all .pdf/.docx/.pptx files in the folder are ingested in batches of 4 → aggregate progress (`12 / 47 · 3 failed`) + per-file errors are shown → wiki generation is offered at completion.
2. Dropzone on the notebook detail page (`/notebooks/[id]`) accepts .pdf, .docx, and .pptx files.
3. Notebook page has a URL input that ingests a web page via `POST /notebooks/{id}/ingest/url`.

All three features are tested and working on desktop Chrome/Firefox.

## Acceptance Criteria

### folder-ingest.AC1: Folder ingestion wizard

- **folder-ingest.AC1.1 Success:** "📂 Import Folder" button is visible on the `/notebooks` page alongside "New Notebook"
- **folder-ingest.AC1.2 Success:** Clicking the button opens the 4-step Dialog at step 1 (file picker)
- **folder-ingest.AC1.3 Success:** Step 1 displays count of valid files (`.pdf`/`.docx`/`.pptx`) and count of filtered-out files (unsupported extensions); "Next" is enabled only when ≥1 valid file is selected
- **folder-ingest.AC1.4 Success:** Step 3 aggregate counter increments as files complete (`N / M · X failed`)
- **folder-ingest.AC1.5 Success:** Failed files appear in a scrollable per-file error list in step 3
- **folder-ingest.AC1.6 Success:** No more than 4 files are uploaded concurrently at any point
- **folder-ingest.AC1.7 Success:** Step 4 "Generate Wiki" button fires `POST /notebooks/{id}/wiki` and dismisses (fire-and-forget)
- **folder-ingest.AC1.8 Success:** Step 4 "View Notebook →" navigates to `/notebooks/{id}`
- **folder-ingest.AC1.9 Failure:** Dialog X button and Cancel are disabled while step 3 upload is running
- **folder-ingest.AC1.10 Failure:** "Start Import →" button is disabled when step 2 notebook name field is empty
- **folder-ingest.AC1.11 Failure:** Notebook creation (`POST /notebooks`) failure shows an error in the Dialog; wizard stays on step 2

### folder-ingest.AC2: Multi-format Dropzone

- **folder-ingest.AC2.1 Success:** Dropzone on the notebook page (`/notebooks/[id]`) accepts `.pdf`, `.docx`, and `.pptx` files
- **folder-ingest.AC2.2 Success:** When `accept` prop is omitted, Dropzone defaults to accepting `.pdf` only (backward-compatible default — `/documents` page stays PDF-only intentionally)
- **folder-ingest.AC2.3 Failure:** Dropzone rejects files with unsupported extensions (e.g. `.txt`, `.jpg`) with a descriptive toast error

### folder-ingest.AC3: URL ingest UI

- **folder-ingest.AC3.1 Success:** Submitting a valid URL from the notebook page calls `POST /notebooks/{id}/ingest/url` and shows `toast.success`; input clears on success
- **folder-ingest.AC3.2 Failure:** A failed ingest request shows `toast.error`; input is not cleared
- **folder-ingest.AC3.3 Edge:** "Ingest URL" button is disabled and shows a loading indicator while the request is in-flight

## Glossary

- **Notebook**: A named collection in DocQuery that groups documents together and scopes conversations, wiki generation, and suggested questions to that set of documents.
- **R2R collection**: The retrieval-layer counterpart to a notebook inside the R2R service — every notebook has one R2R collection ID; documents ingested into a notebook are registered to that collection so RAG queries are scoped correctly.
- **RAG (Retrieval-Augmented Generation)**: A pattern where a language model's answer is grounded in passages retrieved from a document store rather than relying solely on its training data. DocQuery uses R2R as the retrieval layer.
- **R2R**: The open-source retrieval engine (SciPhi-AI/R2R) that DocQuery wraps. Handles vector storage and RAG query execution. Runs on port 7272.
- **Dropzone**: The `Dropzone.tsx` component — a drag-and-drop file upload surface backed by `react-dropzone`. Used on both the notebook detail page and the global `/documents` page.
- **react-dropzone**: A React library that wraps the browser File API into a declarative component with drag-and-drop, MIME-type filtering, and rejection callbacks.
- **`webkitdirectory`**: A non-standard HTML attribute on `<input type="file">` that makes the browser present a folder picker instead of a file picker. Supported on Chrome and Firefox desktop only; not part of any W3C standard.
- **`useBatchUpload`**: New React hook introduced by this design. Encapsulates concurrent file upload state: per-file status, aggregate counters, and `AbortController`-based cleanup on unmount.
- **`AbortController`**: Browser API that cancels in-flight `fetch` requests. Used by `useBatchUpload` to cancel running uploads if the component unmounts.
- **shadcn/ui**: The component library used throughout the web app (`Dialog`, `Sheet`, `Button`, etc.). Components are copied into the codebase rather than imported as a package.
- **`Dialog`**: A shadcn/ui modal overlay component. Already used by `NotebookGrid.tsx` for the "New Notebook" form; `FolderImportDialog` follows the same pattern.
- **Fire-and-forget fetch**: A `fetch` call where only the HTTP status is checked — no response body, no polling. Used for wiki generation and URL ingest.
- **Wiki generation**: A background job (`POST /notebooks/{id}/wiki`) that uses a Gemini LLM to produce a structured, multi-page wiki summarising all documents in the notebook.
- **`NOTEBOOK_ACCEPT`**: Shared TypeScript constant (from `apps/web/lib/acceptedTypes.ts`) mapping MIME types to file extensions for the three supported formats. Passed as the `accept` prop to `Dropzone` and used by `FolderImportDialog`'s file filter.
- **MIME type**: A string like `application/pdf` that identifies a file's format. Browsers use MIME types when filtering files in `<input type="file">` and drag-and-drop APIs.
- **Concurrency cap**: `useBatchUpload` limits simultaneous uploads to 4 to avoid overwhelming the API or the browser's HTTP connection pool.
- **trafilatura**: Python library used server-side to extract readable article text from URLs. The URL ingest path routes through `web_loader.load_url`, which calls trafilatura.

## Architecture

Three independent features share one entry point: the notebooks section of the web UI. Backend is unchanged throughout — all required endpoints already exist.

### New files

- `apps/web/components/FolderImportDialog.tsx` — 4-step Dialog wizard. Owns all step state (`pick → name → progress → done`). Props: `open: boolean`, `onOpenChange: (v: boolean) => void`, `onImported: (notebookId: string) => void`.
- `apps/web/lib/useBatchUpload.ts` — concurrent upload hook. Consumed only by `FolderImportDialog`.
- `apps/web/lib/acceptedTypes.ts` — shared MIME-type constant used by all upload surfaces.

### Modified files

- `apps/web/components/NotebookGrid.tsx` — adds "📂 Import Folder" button alongside "New Notebook"; renders `<FolderImportDialog>` controlled by `importOpen` boolean, same pattern as the existing create-notebook `Dialog`.
- `apps/web/components/Dropzone.tsx` — gains an `accept?: Record<string, string[]>` prop; default remains `{ "application/pdf": [".pdf"] }` for backward compatibility; rejection toast message becomes derived from the accepted extensions list.
- `apps/web/app/(app)/notebooks/[id]/page.tsx` — passes `NOTEBOOK_ACCEPT` to `Dropzone`; adds URL ingest input below Dropzone inside the existing `<details>` section.

### Key contracts

**`useBatchUpload` hook:**

```ts
type BatchItem = {
  id: string;
  file: File;
  status: "pending" | "uploading" | "done" | "failed";
  error?: string;
};

type UseBatchUploadResult = {
  items: BatchItem[];
  total: number;
  done: number;
  failed: number;
  batchStatus: "idle" | "running" | "complete";
  start: (files: File[], notebookId: string) => void;
};

function useBatchUpload(options?: { concurrency?: number }): UseBatchUploadResult
```

`start()` uploads up to `concurrency` (default 4) files concurrently via `POST /notebooks/{id}/documents`. HTTP response status determines `done` vs `failed` — no polling. `AbortController` cancels in-flight requests on unmount.

**`NOTEBOOK_ACCEPT` constant:**

```ts
export const NOTEBOOK_ACCEPT = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
};
```

**`FolderImportDialog` step machine:**

| Step | Name | What happens |
|------|------|--------------|
| 1 | `pick` | Hidden `<input type="file" webkitdirectory multiple>` triggered by button. Displays file count and filtered-out count (unsupported extensions). Next enabled when ≥1 valid file selected. |
| 2 | `name` | Text input prefilled with folder name; optional description. "Start Import →" calls `POST /notebooks`, then `start(files, newNotebookId)`, then advances to step 3. |
| 3 | `progress` | Aggregate counter `N / M · X failed`; scrollable per-file error list (failed items only). X/Cancel disabled while running. Auto-advances when `batchStatus === "complete"`. |
| 4 | `done` | Summary line `M ingested · X failed`. [Generate Wiki] → `POST /notebooks/{id}/wiki` (fire-and-forget). [View Notebook →] → navigate to `/notebooks/{id}`. |

**URL ingest UI** (notebook page, inside `<details>`, below Dropzone):
- `<input type="url">` + "Ingest URL" button
- `POST /notebooks/{id}/ingest/url` with `{ url }` body
- `toast.success` on 2xx; `toast.error` on failure; input cleared on success; button shows loading state while in-flight

### Browser compatibility note

`webkitdirectory` is supported on Chrome and Firefox desktop only — not Safari iOS or Firefox Android. The attribute is set directly on a hidden `<input type="file">` element triggered by a button; it is not within `react-dropzone`'s API surface and cannot be passed through `Dropzone.tsx`.

## Existing Patterns

Investigation found the following patterns this design follows:

- **shadcn `Dialog`** — `NotebookGrid.tsx` already uses `Dialog` / `DialogContent` / `DialogHeader` / `DialogFooter` for the "New Notebook" form. `FolderImportDialog` follows this exact pattern.
- **shadcn `Sheet`** — `SourcePanel.tsx` uses `Sheet` for the citation PDF viewer. Not used here, but confirms the team is comfortable with overlay primitives.
- **Fire-and-forget fetch** — `notebooks/[id]/page.tsx` already calls `POST /notebooks/{id}/documents` with a plain `fetch`, reading only the HTTP status. The URL ingest UI follows the same pattern.
- **Toast notifications** — `toast.success` / `toast.error` used throughout the app for all user feedback.
- **React hooks for upload logic** — `useUploadQueue.ts` separates upload state from the component tree. `useBatchUpload.ts` follows the same separation.

The `useUploadQueue` hook (used by `/documents` page) is not reused — it polls `/ingest/jobs` (the global ingest path) and processes files serially. `useBatchUpload` is a new hook targeting the notebook-scoped endpoint with concurrent execution.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Multi-Format Dropzone

**Goal:** Make `Dropzone.tsx` configurable for accepted file types and propagate `NOTEBOOK_ACCEPT` to all upload surfaces.

**Components:**
- `apps/web/lib/acceptedTypes.ts` — new file exporting `NOTEBOOK_ACCEPT` constant
- `apps/web/components/Dropzone.tsx` — add optional `accept` prop; derive rejection toast message from accepted extensions; default stays PDF-only (backward compat — `/documents` page remains unchanged)
- `apps/web/app/(app)/notebooks/[id]/page.tsx` — pass `NOTEBOOK_ACCEPT` to its `Dropzone`
- `apps/web/components/__tests__/` — update existing Dropzone tests to cover `.docx`/`.pptx` acceptance, default PDF-only behavior, and dynamic rejection message

**Dependencies:** None (standalone change)

**Done when:** Dropzone accepts `.pdf`, `.docx`, `.pptx` when passed `NOTEBOOK_ACCEPT`; defaults to PDF-only when `accept` is omitted; rejects other types with correct toast message; all existing and new Dropzone tests pass; `folder-ingest.AC2.1`, `folder-ingest.AC2.2`, `folder-ingest.AC2.3` covered by tests.
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: `useBatchUpload` Hook

**Goal:** Implement concurrent, notebook-scoped batch upload with per-file state tracking, dedup, and abort.

**Components:**
- `apps/web/lib/useBatchUpload.ts` — new hook with `BatchItem` type and `UseBatchUploadResult` interface as specified in Architecture; uses `GET /notebooks/{id}/documents` for dedup, `POST /notebooks/{id}/documents` for upload, `AbortController` for cleanup

**Dependencies:** Phase 1 (`NOTEBOOK_ACCEPT` constant available)

**Done when:** Hook correctly caps concurrency at 4, per-file status transitions through `pending → uploading → done/failed`, abort on unmount cancels in-flight requests, all tests pass; covers `folder-ingest.AC1.4`, `folder-ingest.AC1.5`, `folder-ingest.AC1.6`.
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: `FolderImportDialog` + `NotebookGrid` Integration

**Goal:** Build the 4-step wizard and wire it into the notebooks list page.

**Components:**
- `apps/web/components/FolderImportDialog.tsx` — 4-step Dialog component consuming `useBatchUpload`; hidden `<input webkitdirectory>` for folder selection; step state machine as specified; wiki offer on step 4
- `apps/web/components/NotebookGrid.tsx` — add "📂 Import Folder" button and `importOpen` state; render `<FolderImportDialog onImported={...} />`

**Dependencies:** Phase 2 (`useBatchUpload` hook)

**Done when:** Full 4-step flow works end-to-end — folder selected, notebook created, files ingested with progress, wiki offer appears; component tests cover step transitions, `POST /notebooks` called before upload starts, `POST /notebooks/{id}/wiki` called on wiki button; covers `folder-ingest.AC1.1`, `folder-ingest.AC1.2`, `folder-ingest.AC1.3`, `folder-ingest.AC1.7`, `folder-ingest.AC1.8`.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: URL Ingest UI

**Goal:** Add a URL input to the notebook page so users can ingest web pages.

**Components:**
- `apps/web/app/(app)/notebooks/[id]/page.tsx` — URL input field and "Ingest URL" button inside the existing `<details>` section below `Dropzone`; calls `POST /notebooks/{id}/ingest/url`; toast feedback; loading state on button

**Dependencies:** None (standalone change; Phase 1 must be complete for the multi-format Dropzone on the same page)

**Done when:** URL input submits to correct endpoint, `toast.success` on 2xx, `toast.error` on failure, input clears on success, button disabled while in-flight; component tests cover success and error paths; covers `folder-ingest.AC3.1`, `folder-ingest.AC3.2`, `folder-ingest.AC3.3`; all four phases manually verified end-to-end on desktop Chrome and Firefox.
<!-- END_PHASE_4 -->

## Additional Considerations

**Cancel during ingest:** The Dialog X button is disabled while step 3 is running. If the user force-closes the browser tab mid-upload, in-flight requests complete or time out server-side; the notebook will contain a partial set of documents. This is acceptable — the user can open the notebook and drop the remaining files via Dropzone.

**Folder picker and `react-dropzone`:** `webkitdirectory` cannot be set via `react-dropzone`'s `accept` prop — it is a non-standard HTML attribute on the underlying `<input>`. The folder picker in `FolderImportDialog` uses a separate hidden `<input type="file" webkitdirectory multiple>` and is not a `Dropzone` instance.
