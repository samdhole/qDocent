# Cite and Scope: NotebookLM-style Citation UX + Query Scoping

## Summary

Citations in DocQuery's chat UI currently appear as a flat list with no hover preview, and every query searches the entire document corpus regardless of user intent. This design adds four additive features — hover-preview citation cards, inline `[N]` chips in answer prose, a documents-only/general-knowledge toggle, and a per-message `#document` picker — to close the gap with NotebookLM-style citation UX.

The approach is strictly additive: no existing routes, components, or data contracts are replaced. On the backend, a new pure functional module (`citation_marker_rewriter`) post-processes R2R's raw `[shortid]` markers into ordered `[N]` references after retrieval; the same function handles the doc-only fallback check. On the frontend, a new `CitationBadge` component wraps a Radix HoverCard and reads shared state from a `CitationContext` provider; a remark plugin converts numeric brackets in markdown into these badges at parse time; and `ChatInput` gains a keyboard-navigable combobox for scoping a single message to one document. All four features ship behind the existing routing with no new public endpoints.

## Definition of Done

**Primary deliverables (4 features in DocQuery's chat UI):**

1. **Hover-preview citations** — every citation marker (both inline `[1]` chips and the citations-panel list) shows a hover card with verbatim quoted text (~400 chars) + page number + doc name.
2. **Inline `[1][2]` chips in answer markdown** — backend adapter replaces R2R's raw `[shortid]` markers with numeric `[N]` matching citation index; frontend renders them as the same hover-card-enabled CitationBadge component.
3. **Documents-only / General-knowledge toggle** — visible toggle near the chat input. State persisted in localStorage. Documents-only mode enforced via R2R prompt override + post-hoc empty-retrieval check that returns "I couldn't find this in your documents." verbatim.
4. **`#document` picker in chat input** — typing `#` opens a list of ingested docs (from `GET /documents`); selection attaches a chip to that single message; chip clears after send. Backend filters R2R search to that document's `r2r_document_ids` for that one query.

**Success criteria:**
- Citations are clickable AND hoverable in both inline and panel form, with no regression on existing SourcePanel behavior.
- Doc-only mode visibly returns "not found" messaging instead of hallucinated answers when retrieval misses.
- `#` picker is keyboard-navigable (arrow keys, enter, escape).
- All four ship behind the existing routing (no new pages).

**Out of scope:**
- Multi-doc selection in `#` picker (one doc per message)
- Conversation history persistence (still per-session)
- Streaming the bracket-replacement during token stream (post-process happens on the `final` event only)
- Changes to RAGAS eval pipeline
- New backend endpoints beyond optional query params on existing ones

## Acceptance Criteria

### cite-and-scope.AC1: Hover-preview citations
- **cite-and-scope.AC1.1 Success:** Mouse hover on a citation badge (inline or panel variant) opens HoverCard content within 200ms (Radix `openDelay` ≈ 150ms).
- **cite-and-scope.AC1.2 Success:** HoverCard content displays the full verbatim `retrievedContexts[index-1].text` (~400 chars), the source `document` name, and `p.{page}` footer.
- **cite-and-scope.AC1.3 Success:** Click or Enter on a focused citation badge invokes `onSelectCitation` from context, opening the existing `SourcePanel` at the cited page (no regression on existing flow).
- **cite-and-scope.AC1.4 Failure:** Citation `index` outside the citations array renders a greyed "missing" fallback chip with no hover content; does not crash the render tree.
- **cite-and-scope.AC1.5 Edge:** Touch-tap on mobile opens SourcePanel directly (no hover required); HoverCard does not intercept tap.

### cite-and-scope.AC2: Inline `[N]` chips end-to-end
- **cite-and-scope.AC2.1 Success:** Backend `rewrite_brackets` maps known `[shortid]` (chunk_id first 7 hex chars) to `[N]` matching the citation's reordered index in answer text.
- **cite-and-scope.AC2.2 Success:** `rewrite_brackets` reorders the `citations` list so `[1]` is the first cited chunk in prose order; uncited citations append at the end preserving R2R relevance order.
- **cite-and-scope.AC2.3 Failure:** Unknown `[shortid]` (not in citations) passes through the rewriter unchanged in answer text; citations list is unaffected.
- **cite-and-scope.AC2.4 Edge:** `rewrite_brackets` with an empty citations list returns answer text unchanged (no-op); does not raise.
- **cite-and-scope.AC2.5 Success:** `remarkCitationBadges` plugin replaces `\[(\d+)\]` matches in markdown with `<cite-ref data-num="N">` hast nodes; `react-markdown` `components` map renders them as `<CitationBadge variant="inline" index={N} />`.
- **cite-and-scope.AC2.6 Edge:** Numeric brackets inside code blocks or inline code are NOT replaced by the remark plugin (remark default behavior; verify in test).

### cite-and-scope.AC3: Documents-only / General toggle
- **cite-and-scope.AC3.1 Success:** Toggle state set to `"general"` persists in `localStorage` across page reload; `useQueryMode` hydrates with the stored value.
- **cite-and-scope.AC3.2 Success:** `doc_only=True` with empty `retrieved_contexts` returns `answer == "I couldn't find this in your documents."` and `confidence_label == "low"`.
- **cite-and-scope.AC3.3 Success:** `doc_only=True` with non-empty retrieval but `confidence_label == "low"` (top score < 0.50) returns the same strict not-found string.
- **cite-and-scope.AC3.4 Success:** `doc_only=True` with valid high-confidence retrieval returns the LLM's answer unchanged (modulo bracket rewriting).
- **cite-and-scope.AC3.5 Success:** `doc_only=False` (general mode) preserves existing behavior — LLM may answer from prior knowledge if retrieval is weak.
- **cite-and-scope.AC3.6 Edge:** When the strict not-found string is returned in doc-only mode, `AnswerCard`'s amber banner shows the "Switch to General knowledge to broaden" CTA.

### cite-and-scope.AC4: `#` document picker
- **cite-and-scope.AC4.1 Success:** Typing `#` followed by characters in `ChatInput` opens the picker listbox with documents from `GET /documents` filtered by case-insensitive `source_file` substring match (max 8 visible).
- **cite-and-scope.AC4.2 Success:** Arrow Down/Up moves `aria-activedescendant` highlight; Enter selects the highlighted document, removes the `#token` from input text, attaches the doc as a chip; picker closes.
- **cite-and-scope.AC4.3 Success:** When `attachedDoc` is set, `useConversationStream.sendMessage` includes `document_id` in POST body; backend resolves to `r2r_document_ids` via `load_document_manifest` and applies `search_settings.filters = {"document_id": {"$overlap": ids}}`.
- **cite-and-scope.AC4.4 Success:** Chip clears (and `attachedDoc` resets to `null`) after submit, regardless of stream success or failure (per-message scope).
- **cite-and-scope.AC4.5 Edge:** Escape closes picker without selecting; Tab also closes picker.
- **cite-and-scope.AC4.6 Edge:** Empty documents list → typing `#` is a no-op (no popover).
- **cite-and-scope.AC4.7 Failure:** Document with no `r2r_document_ids` in manifest → backend skips filter (logs warning) and falls back to unscoped retrieval rather than returning zero results.

## Glossary

- **R2R**: Open-source RAG framework that handles document storage, vector retrieval, and LLM-augmented answer generation; runs as a local server on port 7272.
- **RAG (Retrieval-Augmented Generation)**: Pattern where a language model's answer is grounded by fetching relevant document chunks before generating a response.
- **shortid**: R2R's internal citation marker format — the first 7 hex characters of a chunk's UUID — emitted as `[shortid]` in raw answer text before rewriting.
- **`rewrite_brackets`**: New pure-function backend entry point that maps `[shortid]` tokens to `[N]` and reorders the citations list to match prose order.
- **FCIS (Functional Core / Imperative Shell)**: Architecture pattern enforced in `apps/api/`; pure functions (FC) handle data transformation, I/O orchestrators (IS) call them and R2R.
- **`remarkCitationBadges`**: A remark AST plugin that replaces `[N]` literal text in markdown with custom `<cite-ref>` hast nodes at parse time.
- **hast node**: HTML Abstract Syntax Tree node — the intermediate representation remark/rehype uses before serializing to React elements.
- **`CitationContext`**: React context provider in `AnswerCard` that shares the `citations`, `retrievedContexts`, and `onSelectCitation` callback so any descendant `CitationBadge` can read citation data without prop drilling.
- **`CitationBadge`**: New React component with `inline` and `panel` variants; wraps a Radix HoverCard trigger and falls back to the existing SourcePanel on click.
- **Radix HoverCard**: Headless, accessible UI primitive (`radix-ui` package) providing the hover-activated popover behaviour used for citation previews.
- **SourcePanel**: Existing DocQuery component that displays the full source document view; citation clicks open it at the cited page (unchanged by this design).
- **`useQueryMode`**: New React hook persisting the `"documents" | "general"` toggle state to `localStorage`.
- **`doc_only`**: New optional boolean on `MessageRequest`; when `true`, triggers both a prompt override and a post-hoc empty/low-confidence check that substitutes a strict not-found string.
- **`search_settings.filters`**: R2R SDK parameter that restricts vector search to a subset of documents; set per-request (without mutating the default) when a `#document` chip is attached.
- **`load_document_manifest`**: Existing backend helper that resolves a DocQuery `document_id` to its list of `r2r_document_ids` (R2R's internal IDs for the chunks of that document).
- **`mdast-util-find-and-replace`**: Utility (transitive dependency of remark) used inside `remarkCitationBadges` to walk the markdown AST and replace text nodes matching `[N]`.
- **SSE (Server-Sent Events)**: Transport used by `/conversations/{id}/messages/stream`; the bracket rewriter runs only on the `final` event, not on streaming token chunks.
- **ARIA combobox pattern**: WAI-ARIA interaction model (`role="combobox"`, `aria-expanded`, `aria-activedescendant`) used for the accessible `#` document picker listbox.
- **RAGAS**: Evaluation framework (not modified by this design) that scores retrieval quality; mentioned in scope boundaries.

## Architecture

DocQuery's chat UI gains four features applied additively across `apps/web/` (Next.js) and `apps/api/` (FastAPI/R2R). No existing components are rewritten; all four features ride existing routes with optional request fields.

**Key data flow:**

```
[ChatInput] ──text + opt(docOnly, documentId)──▶ /conversations/{id}/messages/stream
                                                            │
                                                            ▼
                                       r2r_agent.agent_stream(...)
                                            │       │
                          (a) prompt override         (c) search_settings.filters
                          when docOnly=True            when documentId provided
                                            │       │
                                            ▼       ▼
                                     R2R retrieval.agent SDK
                                            │
                                            ▼
                          _adapt_final_event / _adapt_agent_response
                                            │
                                ┌───────────┴────────────┐
                                ▼                        ▼
                  citation_marker_rewriter      doc-only post-hoc check
                  ([shortid]→[N], reorder)      (empty/low → strict not-found)
                                            │
                                            ▼
                                    AskResponse-shaped dict
                                            │
                                            ▼
                  [AnswerCard]: CitationContext.Provider
                  ├── ReactMarkdown(remarkCitationBadges) → <CitationBadge variant=inline>
                  └── citations.map → <CitationBadge variant=panel>
                                            │
                                  Each CitationBadge wraps Radix HoverCard
                                  + onClick → existing SourcePanel
```

**Frontend boundaries:** `ChatInput` owns text + picker state; `useConversationStream` owns network/streaming; `AnswerCard` + `CitationContext` own citation rendering.

**Backend boundaries:** `citation_marker_rewriter` is a pure functional core module; `r2r_agent` is the imperative shell that invokes it after R2R returns.

**Key contracts:**

```python
# apps/api/services/citation_marker_rewriter.py
def rewrite_brackets(answer: str, citations: list[dict]) -> tuple[str, list[dict]]:
    """Replace R2R [shortid] markers with [N]; reorder citations to match prose order.
    Unknown shortids pass through unchanged. Empty citations list → no-op."""
```

```python
# apps/api/routes/conversations.py
class MessageRequest(BaseModel):
    message: str
    doc_only: bool = False
    document_id: str | None = None
```

```typescript
// apps/web/components/CitationContext.tsx
type CitationContextValue = {
  citations: Citation[];
  retrievedContexts: RetrievedContext[];   // index-aligned with citations[]
  onSelectCitation?: (sel: SelectedCitation) => void;
};
```

```typescript
// apps/web/components/CitationBadge.tsx
type Props = {
  index: number;                                     // 1-based, matches [N] in prose
  variant?: "inline" | "panel";                      // default "inline"
};
// All citation/onSelect data sourced from CitationContext.
```

```typescript
// apps/web/components/ChatInput.tsx
type ChatInputProps = {
  pending: boolean;
  documents: SourceDocument[];                       // fetched once from GET /documents
  onSubmit: (text: string, attached?: SourceDocument) => void;
};
```

```typescript
// apps/web/lib/useQueryMode.ts
type QueryMode = "documents" | "general";
function useQueryMode(): [QueryMode, (m: QueryMode) => void];
// Backed by localStorage key "docquery.queryMode"; default "documents".
```

```typescript
// apps/web/lib/useConversationStream.ts
sendMessage(text: string, opts?: { docOnly?: boolean; documentId?: string }): Promise<void>;
```

## Existing Patterns

Investigation found multiple existing patterns this design follows:

- **Unified `radix-ui` import style.** `apps/web/components/ui/dropdown-menu.tsx` uses `import { DropdownMenu as DropdownMenuPrimitive } from "radix-ui"`. The new `ui/hover-card.tsx` follows this exact convention rather than the legacy per-package `@radix-ui/react-hover-card` import.
- **Functional Core / Imperative Shell (FCIS).** Every Python module in `apps/api/` starts with `# pattern: Functional Core` or `# pattern: Imperative Shell`. The new `citation_marker_rewriter.py` is FC; edits to `r2r_agent.py` keep it as IS.
- **Descriptive module names.** Per `CLAUDE.md`, no generic `utils.py` / `helpers.py`. New modules use specific names (`citation_marker_rewriter.py`, `remarkCitationBadges.ts`, `useQueryMode.ts`).
- **Index-aligned citations + retrieved_contexts.** `r2r_agent._adapt_agent_response` already constructs `citations[i]` and `retrieved_contexts[i]` in the same loop. The frontend now relies on this alignment; the rewriter preserves it during reorder.
- **Citation click → SourcePanel.** `AnswerCard` already passes `onSelectCitation` upward to `ConversationView`, which manages `selectedCitation` state and lazy-loads `SourcePanel`. The new `CitationBadge` reads `onSelectCitation` from context and preserves this flow end-to-end.
- **Streaming SSE adapter symmetry.** `r2r_agent._adapt_final_event` reuses `_adapt_agent_response` by constructing a synthetic response. Both bracket post-processing and doc-only post-hoc check live in `_adapt_agent_response` — single source of truth across streaming and non-streaming paths.
- **Frontend test layout.** `apps/web/lib/__tests__/bboxConversion.test.ts` shows the Vitest pattern. New hooks (`useQueryMode`) and pure functions get tests alongside; component tests use Vitest + RTL.
- **60/30/10 rule (per CLAUDE.md).** Bracket rewriting is fully deterministic regex (60% camp); the doc-only prompt override is the only LLM-touching change (10% camp); the rest is rule-based orchestration (30% camp).

No new patterns are introduced.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Backend bracket rewriter

**Goal:** Replace R2R's raw `[shortid]` markers with numeric `[N]` markers in answer text and reorder citations to match prose order.

**Components:**
- `citation_marker_rewriter` in `apps/api/services/citation_marker_rewriter.py` — pure functional core module exposing `rewrite_brackets(answer, citations) -> (rewritten_answer, reordered_citations)`. Builds a `shortid → index` map (chunk_id first 7 hex chars), regex-replaces `\[([0-9a-f]{6,8})\]`, preserves first-seen order. Unknown shortids pass through unchanged. Empty citations list → no-op.
- Edit to `apps/api/services/r2r_agent.py` — `_adapt_agent_response` calls `rewrite_brackets` after building citations/retrieved_contexts, before the figures lookup. The same call covers both `agent_query` (non-streaming) and `agent_stream` (via `_adapt_final_event`'s reuse of `_adapt_agent_response`).

**ACs covered:** `cite-and-scope.AC2.1`, `cite-and-scope.AC2.2`, `cite-and-scope.AC2.3`

**Dependencies:** None (first phase).

**Done when:** `tests/test_citation_marker_rewriter.py` passes, including: known-shortid mapping, unknown-shortid passthrough, citation reorder so `[1]` is first cited, no-citations no-op, malformed answer text passthrough. Existing `tests/test_r2r_agent.py` still passes (regression check).
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: CitationBadge + HoverCard primitive

**Goal:** Visually replace the existing flat citations list with hover-preview-enabled badges. Inline variant unused at this phase but available.

**Components:**
- `HoverCard` shadcn-style wrapper in `apps/web/components/ui/hover-card.tsx` — exports `HoverCard`, `HoverCardTrigger`, `HoverCardContent`. Imports from unified `radix-ui` per existing dropdown-menu.tsx convention.
- `CitationContext` in `apps/web/components/CitationContext.tsx` — Provider exposing `{ citations, retrievedContexts, onSelectCitation? }`.
- `CitationBadge` in `apps/web/components/CitationBadge.tsx` — single component, `variant: "inline" | "panel"`. Wraps Radix HoverCard with `openDelay` ≈ 150ms. Trigger is a real `<button>` with `onClick` invoking `onSelectCitation` from context. Hover content shows `retrievedContexts[index-1].text` with `p.{page} · {document}` footer and an "Open source" link.
- Edit to `apps/web/components/AnswerCard.tsx` — wrap markdown in `<CitationContext.Provider>`. Replace the existing `<ul>/<li>` citation list rendering with `citations.map((_, i) => <CitationBadge variant="panel" index={i+1} />)`.

**ACs covered:** `cite-and-scope.AC1.1`, `cite-and-scope.AC1.2`, `cite-and-scope.AC1.3`, `cite-and-scope.AC1.4`

**Dependencies:** Phase 1 (rewriter has run, so [N]-indexed citations land in context).

**Done when:** Component tests pass for `CitationBadge` (inline + panel render, hover triggers HoverCard content, click invokes `onSelect`, out-of-bounds index renders fallback chip without crashing). Manual: existing SourcePanel click flow unchanged.
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Remark plugin for inline `[N]` chips

**Goal:** Replace numeric `[N]` markers in rendered answer markdown with inline `CitationBadge` instances at parse time.

**Components:**
- `remarkCitationBadges` in `apps/web/lib/remarkCitationBadges.ts` — remark plugin using `mdast-util-find-and-replace` (transitive dep of remark; no new package). Replaces `/\[(\d+)\]/g` with a hast node `{ type: "citationRef", data: { hName: "cite-ref", hProperties: { "data-num": num } }, children: [] }`. Custom hyphenated tag `cite-ref` (valid HTML custom element name).
- Edit to `apps/web/components/AnswerCard.tsx` — add `remarkCitationBadges` to `remarkPlugins`; map `"cite-ref"` in the `components` prop to `<CitationBadge variant="inline" index={Number(props["data-num"])} />`.
- Edit to `apps/web/components/ConversationView.tsx` — add the same plugin to the partial-stream `<ReactMarkdown>` render (consistency, even though raw `[shortid]` may transit there during stream).

**ACs covered:** `cite-and-scope.AC1.5`, `cite-and-scope.AC2.4`

**Dependencies:** Phase 2 (`CitationBadge` exists with `inline` variant; `CitationContext` available).

**Done when:** Plugin unit test passes (fixture markdown → asserted hast nodes with correct `data-num`). Component test on `<ReactMarkdown>` with the plugin renders `<CitationBadge variant="inline">` children. Manual: an answer with `[1] [2]` text renders as two clickable, hoverable inline chips.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Documents-only toggle

**Goal:** User-controllable toggle between "documents only" (strict, with not-found fallback) and "general" (existing behavior). Toggle state persists across reload.

**Components:**
- `useQueryMode` hook in `apps/web/lib/useQueryMode.ts` — returns `[QueryMode, setMode]`. Reads/writes localStorage key `"docquery.queryMode"`. SSR-safe lazy init via `useEffect`. Default `"documents"`.
- `QueryModeToggle` in `apps/web/components/QueryModeToggle.tsx` — compact two-button segmented control (Docs / General) with hover tooltip explaining each mode.
- Edit to `apps/web/components/ConversationView.tsx` — render `<QueryModeToggle>` left of input; pass `docOnly: queryMode === "documents"` into `sendMessage`.
- Edit to `apps/web/lib/useConversationStream.ts` — extend `sendMessage(text, opts?)` signature; serialize `doc_only` and `document_id` into POST body when present.
- Edit to `apps/api/routes/conversations.py` — `MessageRequest` gains `doc_only: bool = False` and `document_id: str | None = None`.
- Edit to `apps/api/services/r2r_agent.py` — `agent_query` and `agent_stream` accept `doc_only`. When true, pass `task_prompt_override` via `rag_generation_config`. After `_adapt_agent_response`, if `doc_only` and (`retrieved_contexts == []` or `confidence_label == "low"`), replace `answer` with `"I couldn't find this in your documents."`, force `confidence_label="low"`, `needs_human_review=True`.
- Edit to `apps/web/components/AnswerCard.tsx` — extend the `isLowConfidenceNoContext` banner: when the answer text matches the strict not-found string, show "Switch to General knowledge to broaden" CTA.

**ACs covered:** `cite-and-scope.AC3.1`, `cite-and-scope.AC3.2`, `cite-and-scope.AC3.3`, `cite-and-scope.AC3.4`, `cite-and-scope.AC3.5`

**Dependencies:** Phase 1 (rewriter runs before post-hoc check so `confidence_label` is final).

**Done when:** Hook test for `useQueryMode` localStorage roundtrip passes. Backend tests on `agent_query` with `doc_only=True` cover: empty contexts → strict not-found; low confidence → strict not-found; valid retrieval → unchanged. Manual: toggle persists across reload; "Switch to General" CTA visible after a not-found.
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: `#` document picker + ChatInput component

**Goal:** Typing `#` opens a doc picker; selection attaches a per-message chip; backend filters retrieval to that doc's `r2r_document_ids`.

**Components:**
- `ChatInput` in `apps/web/components/ChatInput.tsx` — owns `text`, `attachedDoc`, `pickerOpen`, `pickerQuery`, `highlightIndex`. Plain `<input>` with `role="combobox"` + ARIA combobox attributes (`aria-expanded`, `aria-controls`, `aria-activedescendant`). `onChange` detects fresh `#token` in text-up-to-caret; opens listbox below input. Listbox uses `role="listbox"` with `role="option"` children, max 8 filtered docs. Caret-anchored popover via hidden mirror `<span>` + `getBoundingClientRect`. Keyboard: Arrow up/down moves `highlightIndex`, Enter selects, Escape/Tab closes. Selection: removes `#token` from text, sets `attachedDoc`, closes picker, renders chip left of input with "x" to clear. One mention max.
- Edit to `apps/web/components/ConversationView.tsx` — replace the inline form with `<ChatInput documents={...} onSubmit={...} pending={pending} />`. One-time `useEffect` fetch of `GET /documents` on mount; thread the result into `ChatInput`.
- Edit to `apps/web/lib/useConversationStream.ts` — `sendMessage` already accepts `opts.documentId` from Phase 4; no further change here.
- Edit to `apps/api/services/r2r_agent.py` — when `document_id` is provided, call `document_store.load_document_manifest(document_id)`, extract `r2r_document_ids`, set per-request `search_settings.filters = {"document_id": {"$overlap": ids}}`. `DEFAULT_SEARCH_SETTINGS` is not mutated.

**ACs covered:** `cite-and-scope.AC4.1`, `cite-and-scope.AC4.2`, `cite-and-scope.AC4.3`, `cite-and-scope.AC4.4`, `cite-and-scope.AC4.5`

**Dependencies:** Phase 4 (`document_id` already plumbed through `MessageRequest` and `sendMessage`).

**Done when:** ChatInput tests pass: `#` opens picker, arrow keys move highlight, Enter selects + closes picker, Escape closes, chip clears post-submit. Backend test: filter merge — `document_id` arg → `search_settings.filters` includes `$overlap` on `r2r_document_ids`. Manual test plan added at `docs/test-plans/2026-05-09-cite-and-scope.md` covering all 4 features end-to-end.
<!-- END_PHASE_5 -->

## Additional Considerations

- **Streaming transient state.** During token streaming, partial answer text may show raw `[shortid]` markers transiently; the bracket rewriter only runs on the final event. The swap from `partialText` to the rewritten final answer is fast enough that this is acceptable.
- **Empty documents state.** Typing `#` with zero ingested docs is a no-op (no popover). The picker hint area suggests ingesting documents first.
- **HoverCard accessibility caveat.** Radix HoverCard is documented as "intended for sighted users only." Mitigation: the trigger is a real `<button>`; click/Enter open the SourcePanel (the existing accessible flow). Hover preview is purely additive for mouse users.
- **Citation ordering invariant.** `citations[i]` and `retrieved_contexts[i]` must remain index-aligned through the rewriter's reorder step. The rewriter reorders both arrays in lockstep.
- **No new endpoints.** All four features ride existing routes (`POST /conversations/{id}/messages/stream`, `GET /documents`) with optional fields. No version bump or new public surface.
