# Dependency Licenses

This project uses the following major dependencies. All Python deps are listed in
`requirements.txt`; all frontend deps are listed in `apps/web/package.json`.

## ⚠️ PyMuPDF — AGPL-3.0 (action required for closed-source deployments)

**PyMuPDF** (`pymupdf`) is published by Artifex Software under **AGPL-3.0**. This
license requires any software that incorporates PyMuPDF — including software offered
as a network service — to release its full source code under the same terms, unless a
separate commercial license is obtained from Artifex.

**Action required for closed-source deployments:**
Contact Artifex (https://artifex.com/licensing/) to obtain a commercial PyMuPDF license
before deploying qDocent as a closed-source or proprietary service.

PyMuPDF is used in `packages/ingestion/` for figure extraction and layout-aware PDF
parsing. It is not involved in retrieval, evaluation, or the API layer.

---

## Python Dependencies

| Package | License | Notes |
|---|---|---|
| pymupdf | **AGPL-3.0** | ⚠️ Closed-source deployment requires Artifex commercial license |
| r2r | Apache 2.0 | |
| ragas | Apache 2.0 | |
| langchain-google-genai | MIT | |
| langgraph | MIT | |
| datasets | Apache 2.0 | |
| pandas | BSD 3-Clause | |
| fastapi | MIT | |
| uvicorn | BSD 3-Clause | |
| pydantic | MIT | |
| python-dotenv | BSD 3-Clause | |
| httpx | BSD 3-Clause | |
| python-multipart | Apache 2.0 | |
| pdfplumber | MIT | |
| Pillow | HPND (MIT-like) | |
| pytesseract | Apache 2.0 | |
| camelot-py | MIT | |
| tabulate | MIT | |
| pyyaml | MIT | |

## Frontend Dependencies (apps/web)

| Package | License |
|---|---|
| next | MIT |
| react / react-dom | MIT |
| tailwindcss | MIT |
| radix-ui | MIT |
| lucide-react | ISC |
| react-pdf | MIT |
| pdfjs-dist | Apache 2.0 |
| react-markdown | MIT |
| react-dropzone | MIT |
| vitest | MIT |
| typescript | Apache 2.0 |

> **Note:** License classifications above are based on each package's published PyPI /
> npm metadata. Always verify against the exact version in use before a production
> deployment — licenses can change across major versions.
