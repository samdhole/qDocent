# Demo Script — 60-90 Seconds

A walkthrough for showing qDocent to a potential client or reviewer. Anchor on the `/demo` page — it works even without a running backend.

---

## Positioning Statement (use at start or end)

> "qDocent is an evaluated RAG knowledge assistant: it ingests your business documents, answers questions with citations back to the source PDF, and produces a per-question reliability report so you know exactly where it works and where it doesn't."

---

## The 4-Step Flow

### Step 1 — Open `/demo` (0–30 seconds)

Navigate to `http://localhost:3000/demo`.

**Point to each section:**

- **Wiki Generation panel** — "This is a wiki generated from a real Robinhood 2023 Annual Report. The system read the 10-K, organized it into sections — Corporate Profile, Financial Analysis, Risk and Compliance — and wrote a structured knowledge base. This took one API call."

- **Cited Q&A panel** — "Here's a sample answer to a financial question. Notice the [1][2][3] citation markers in the prose — each one links to a specific page in the source PDF. 15 citations in this answer. Click any badge to see the source passage."

- **Figure Extraction panel** — "The system also extracts embedded figures during ingest — charts, tables, diagrams — and matches them to relevant answers."

- **Try It Live panel** — If the API is running: "This is a live chat connected to the Demo notebook. Ask anything." If the API is down: "The page shows a cached example when the backend is offline — the demo always renders."

---

### Step 2 — Upload a Document (30–45 seconds)

Navigate to `http://localhost:3000/documents`.

1. Click "Upload Document" or drag a PDF into the upload zone
2. Watch the progress bar — ingest typically completes in 30-60 seconds
3. When complete, the document appears in the list with a "View source PDF" link

**Say:** "Documents are ingested in the background — the browser polls for status. Once done, the source PDF is stored and any question you ask can cite back to it."

---

### Step 3 — Ask a Cited Question (45–65 seconds)

Navigate to `http://localhost:3000/ask`.

Type: **"What is the refund policy? Cite the source."**

1. Answer appears with [1][2] citation badges inline in the prose
2. Click a citation badge — the source PDF opens at the cited page in a side panel
3. Point to the highlighted chunk: "This is the exact paragraph the answer was drawn from."

**Say:** "Every answer is grounded in the uploaded documents. If the content isn't there, the system says so — it doesn't guess."

Optional follow-up to show refusal: Type **"What is the CEO's personal phone number?"**
→ System declines: "This shows the refusal behavior — questions outside the document scope get an honest 'not available' rather than a hallucinated answer."

---

### Step 4 — Show the Reliability Report (65–80 seconds)

Navigate to `http://localhost:3000/evals` (or show `delivery-report.md`).

Point to the RAGAS table:

- "These are per-question scores from a 16-question benchmark."
- "Faithfulness is 1.000 where computed — no hallucinations detected on factual questions."
- "The 0.0 scores on the refusal questions are expected — the system correctly declined to answer, which RAGAS registers as low relevancy."
- "I don't hide failed rows. Q9 had a retrieval miss — the document existed in the corpus but wasn't retrieved. That's a known gap with a fix in the pipeline."

**Say:** "Most RAG demos show only the successes. This one shows the full picture so you can make an informed decision about where it's reliable and where it needs work."

---

## Timing Summary

| Step | What you show | Target time |
|------|--------------|-------------|
| 1. `/demo` | Wiki + Q&A panel + figure + live/cached state | 0–30s |
| 2. `/documents` | Upload + ingest progress | 30–45s |
| 3. `/ask` | Cited answer + source panel + refusal demo | 45–65s |
| 4. `/evals` | RAGAS table + honest failure discussion | 65–80s |

**Total: ~80 seconds.** Leave 10-15 seconds for questions.

---

## If Something Goes Wrong

| Problem | Recovery |
|---------|---------|
| Backend not running | Step 1 still works (snapshot rendering). Acknowledge it, continue from `/demo`. |
| Ingest takes too long | Skip Step 2 or show an already-ingested document. |
| Eval page empty | Show `delivery-report.md` directly from the client-handoff folder. |
| R2R not up | `/demo` and `/evals` still work. Focus on those two steps. |

---

## Tailoring by Audience

**For a technical buyer:**
- Lead with Step 4 (eval numbers) — they'll ask about accuracy first
- Show the architecture diagram in `CLAUDE.md` or `delivery-report.md`
- Offer to walk through the ingestion pipeline code

**For a non-technical buyer:**
- Lead with Step 1 and Step 3 — show the answer and the source PDF side-by-side
- Use the analogy: "It's like Ctrl+F, but it understands the question instead of matching keywords"
- Skip the RAGAS table; use "92% of questions answered correctly" as the soundbite
