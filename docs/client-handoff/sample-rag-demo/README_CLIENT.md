# qDocent — RAG Document Q&A System
## Client Delivery: Sample RAG Demo

---

## What You're Getting

This delivery is a working **Retrieval-Augmented Generation (RAG) document Q&A system**. In plain terms: upload your business documents, ask questions in plain English, and get answers that cite exactly which page of which document they came from.

Three things are included:

1. **A working Q&A system** — ask questions about uploaded documents and get cited answers within 2-5 seconds. The system only answers from your documents; it doesn't guess or pull from the internet.

2. **Source citations with PDF links** — every answer includes clickable references showing the exact page and section in the source document. No more "I think it says somewhere that…"

3. **A reliability report** — every question can be scored for answer relevancy, context precision, and faithfulness. You get honest numbers, not just "it works great."

---

## How to Try It

### Option 1: Instant Demo (no setup)

The `/demo` page loads from committed snapshots and works without any running backend. Open it at:

```
http://localhost:3000/demo
```

It shows:
- A generated **wiki** from a real Robinhood 2023 Annual Report (10-K filing)
- A sample **cited answer** with 15 source references
- An **extracted figure** from the filing
- A **live chat panel** (if the backend is running) or a cached example if it's not

### Option 2: Full Local Stack

```bash
# 1. Copy environment config
cp .env.example .env
# Edit .env: add your GOOGLE_API_KEY (see api-key-and-deployment-notes.md)

# 2. Set up dependencies
make setup

# 3. Start services (three separate terminals)
make r2r    # starts retrieval server on port 7272
make api    # starts API server on port 8000
make web    # starts web UI on port 3000

# 4. Verify everything is working
python scripts/demo_readiness.py
```

Then open `http://localhost:3000` and start uploading documents.

---

## What to Ask It

Try these with the included demo corpus (Robinhood 2023 10-K):

- *"What are Robinhood's main revenue sources?"*
- *"What were the total net revenues for 2023?"*
- *"What risk factors does Robinhood cite related to competition?"*

For the synthetic policy/pricing documents included in `data/sample_docs/`:

- *"What is the refund policy?"*
- *"What does the Pro plan cost and what support does it include?"*
- *"Who approves enterprise discounts above 20%?"*

---

## What's In This Delivery Folder

| File | What it contains |
|------|-----------------|
| `README_CLIENT.md` | This file |
| `test-questions.md` | 20 benchmark questions with expected behaviors and eval results |
| `delivery-report.md` | RAGAS evaluation metrics, sample Q&A outputs, failure analysis |
| `known-limits.md` | Honest scope boundaries — what works, what doesn't, what's next |
| `api-key-and-deployment-notes.md` | API key setup and local deployment walkthrough |
| `demo-script.md` | 60-90 second demo walkthrough script |
| `../upwork-proposal-template.md` | Reusable Upwork proposal template |

---

## Contact

[Your name / Upwork profile URL]
[Email or preferred contact]

Questions about this delivery or the roadmap to production? See `known-limits.md` for scope and `../upwork-proposal-template.md` for next-phase options.
