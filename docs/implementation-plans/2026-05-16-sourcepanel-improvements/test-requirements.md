# Test Requirements: SourcePanel Improvements

## Automated Test Coverage

Each AC that can be verified by automated test must have a corresponding test. Manual-only criteria are noted.

| Criterion | Test file | Test name | Notes |
|-----------|-----------|-----------|-------|
| AC1.1 (text layer enabled) | Manual only | — | react-pdf's text layer requires a real browser canvas; jsdom stubs it out |
| AC1.2 (overlay still on top) | Manual only | — | z-stacking visual verification requires browser render |
| AC1.3 (tests still pass) | `SourcePanel.test.tsx` | All 14 existing tests | Regression gate — no new test needed |
| AC2.1 (single-page footer: "Page N") | `SourcePanel.test.tsx` | "AC2: footer shows 'Page N' only for single-page citation" | Asserts span text, no "cited pp." suffix |
| AC2.2 (multi-page footer: "Page N · cited pp.X–Y") | `SourcePanel.test.tsx` | "AC2: footer shows 'Page N · cited pp.X–Y' for multi-page citation" | Asserts full footer string. **Manual verification not possible with the standard corpus** — the DocQuery pipeline sets `page_start = page_end = current_page` for every chunk (`chunk_templates.py:120-121`), so all real citations are single-page by design. The multi-page branch is exercised only via the automated test, which injects a synthetic citation (`pageStart:3, pageEnd:7`). |
| AC2.3 (no range suffix when single-page) | `SourcePanel.test.tsx` | Covered by AC2.1 test (`queryByText(/cited pp\./)` assertion) | |
| AC2.4 (no stale assertions on old format) | `SourcePanel.test.tsx` | All existing tests pass | Regression gate |
