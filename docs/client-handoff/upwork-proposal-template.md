# Upwork Proposal Template
## "Build / Fix a RAG Chatbot Over PDFs or Internal Documents"

Use this template for Upwork job postings asking for document Q&A, internal knowledge base AI, RAG chatbots, or "train AI on my documents."

---

## Subject Line

```
[Client Goal from Job Post] → Cited RAG Document Q&A with Eval Report
```

Examples:
- "Internal policy chatbot → Cited RAG Document Q&A with Eval Report"
- "PDF Q&A over 200 contracts → Cited RAG Document Q&A with Eval Report"
- "Customer support AI on your docs → Cited RAG Document Q&A with Eval Report"

---

## Proposal Body

```
Hi [Name],

I build production RAG document Q&A systems. Your project — [restate the 
core ask in one phrase from the job posting] — is exactly the pattern I've 
delivered before.

Here's how I'd approach it:

**Milestone 1 (Proof of Concept)** — 3-5 days
Ingest your documents, run a 10-question benchmark, deliver a working demo 
with per-question accuracy scores. You approve before we go further.

**Milestone 2 (Pipeline Hardening)** — 3-5 days
Multi-format support (PDF, DOCX, PPTX, web URLs), per-document quality 
reports, figure extraction, edge-case handling.

**Milestone 3 (Auth & Scoping)** — 1-2 weeks
Users only see documents they're allowed to see. Org/workspace model, 
roles (admin/editor/viewer), notebook-level access control.

**Milestone 4 (Admin Dashboard)** — 1 week
Manage documents and users from the browser. Ingest status, retry flow, 
health page.

**Milestone 5 (Analytics & Eval)** — 1 week
Question log, unanswered query reports, eval score trends. Proof the 
system is improving over time.

You can start with just Milestone 1 to validate fit before committing to 
the full scope.

---

**Proof of prior work:**
[Link to GitHub repo or hosted /demo page]
Includes: live demo with Robinhood 10-K corpus, 16-question RAGAS eval 
report (faithfulness 1.000 on factual questions), source PDF citation links.

---

**Logistics:**
- Timeline: [X weeks depending on scope]
- Deliverables per milestone: working code, tests, eval report, docs
- Revisions: 2 rounds per milestone
- Post-delivery: 30-day bug fixes included

---

Happy to do a 15-minute call. What document types and user count are you 
working with?

[Your name]
```

---

## Customization Notes

### For "chatbot on my website" postings
Add to Milestone 2: "Embeddable widget or API endpoint for your existing site."
Adjust Milestone 3 timing — auth scope may be simpler (read-only public widget doesn't need full ACLs).

### For "integrate with Slack/Teams" postings
Replace Milestone 4 with: "Slack/Teams bot integration — @mention the assistant in channels, answers appear inline."

### For "I already have a RAG system, fix it" postings
Lead differently:
```
I see you're having [specific issue from posting — latency, hallucinations, 
wrong answers]. I've debugged exactly this. The most common causes are 
[chunking strategy mismatch / embedding model mismatch / missing metadata 
in chunk headers]. Here's what I'd do first...
```
Then offer Milestone 1 as a diagnosis sprint, not a fresh build.

### For "connect to SharePoint / Google Drive / Notion" postings
Add to Milestone 2: "Document source connector: sync from [platform], with last-sync status and retry on failure."

---

## What Makes This Proposal Convert

1. **Milestone 1 first** — reduces buyer risk. They can approve the proof before committing to full scope.
2. **Proof artifact** — link to the actual eval report, not just "I've done this before."
3. **Specific numbers** — "faithfulness 1.000" and "16-question benchmark" are more credible than "high accuracy."
4. **Honest scope** — mentioning what's not in Milestone 1 (no auth, no Docker) builds trust faster than overpromising.
5. **Open question at the end** — invites reply, positions you as a consultant not just a coder.

---

## Pricing Reference (2026 Upwork market)

| Scope | Range |
|-------|-------|
| Milestone 1 only (proof of concept) | $500–$1,500 |
| Milestones 1–2 (working pipeline) | $1,500–$4,000 |
| Milestones 1–3 (with auth) | $4,000–$10,000 |
| Full 5-milestone productized system | $10,000–$25,000 |
| Managed ongoing service (post-delivery) | $500–$2,000/month |

Adjust based on document volume, complexity of source system integration, and client technical sophistication.
