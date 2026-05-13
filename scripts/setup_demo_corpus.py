"""Set up the demo corpus: download Robinhood ARS PDF, ingest, generate wiki, capture snapshots."""
# pattern: Imperative Shell

import json
import os
import shutil
import sys
import time
import urllib.request
import uuid
from pathlib import Path

API_BASE = os.getenv("DOCQUERY_API_BASE_URL", "http://localhost:8000")

EDGAR_HOOD_ARS_URL = (
    "https://www.sec.gov/Archives/edgar/data/1783879/"
    "000119312524118494/d828738dars.pdf"
)
EDGAR_USER_AGENT = "DocQuery Research enigman.kk@gmail.com"

DEMO_NOTEBOOK_NAME = "Demo"
DEMO_QUESTION = (
    "What are this company's main revenue sources and key financial results "
    "for the most recent fiscal year?"
)

WIKI_JSON = Path("apps/web/app/(app)/demo/data/wiki_structure.json")
QA_JSON = Path("apps/web/app/(app)/demo/data/example_qa.json")
FIGURE_PNG = Path("apps/web/public/demo/example_figure.png")
FIGURES_BASE = Path("data/figures")
FILING_PDF = Path("data/do_not_commit/HOOD_10K_2023.pdf")

PLACEHOLDER_PNG_SIZE = 1024  # 1×1 placeholder is ~70 bytes; real figures are several KB+


def _api_get(path: str) -> list | dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _api_post_json(path: str, data: dict) -> dict:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _api_post_empty(path: str) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=b"",
        headers={"Accept": "application/json", "Content-Length": "0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _upload_pdf(notebook_id: str, pdf_path: Path) -> dict:
    boundary = uuid.uuid4().hex
    filename = pdf_path.name
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + pdf_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{API_BASE}/notebooks/{notebook_id}/documents",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def _figure_is_real() -> bool:
    # Threshold: placeholder is ~70 bytes (1×1 PNG); real extracted figures are several KB+.
    # 1024 bytes is a safe boundary that avoids regenerating over any real figure.
    try:
        return FIGURE_PNG.stat().st_size > PLACEHOLDER_PNG_SIZE
    except FileNotFoundError:
        return False


def _get_or_create_notebook() -> str:
    notebooks = _api_get("/notebooks")
    existing = next(
        (nb for nb in notebooks if nb.get("name") == DEMO_NOTEBOOK_NAME), None
    )
    if existing:
        print(f"  Found existing {DEMO_NOTEBOOK_NAME!r} notebook: {existing['id']}")
        return existing["id"]
    resp = _api_post_json(
        "/notebooks",
        {"name": DEMO_NOTEBOOK_NAME, "description": "Demo corpus for /demo page"},
    )
    print(f"  Created {DEMO_NOTEBOOK_NAME!r} notebook: {resp['id']}")
    return resp["id"]


def _download_filing() -> None:
    if FILING_PDF.exists():
        print(f"  PDF already cached: {FILING_PDF}")
        return
    print("  Downloading Robinhood 2023 Annual Report PDF from SEC EDGAR...")
    req = urllib.request.Request(
        EDGAR_HOOD_ARS_URL,
        headers={"User-Agent": EDGAR_USER_AGENT},
    )
    FILING_PDF.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=60) as resp, open(FILING_PDF, "wb") as f:
        f.write(resp.read())
    print(f"  Downloaded: {FILING_PDF} ({FILING_PDF.stat().st_size:,} bytes)")


def _get_existing_doc_id(notebook_id: str) -> str:
    """Return the first document_id already in the notebook, or '' if none."""
    try:
        docs = _api_get(f"/notebooks/{notebook_id}/documents")
        if docs and isinstance(docs, list):
            # Assumes single-document Demo notebook; first doc only.
            doc_id = docs[0].get("document_id") or docs[0].get("id") or ""
            if doc_id:
                print(f"  Notebook already has document: {doc_id} — skipping ingest")
                return doc_id
    except Exception:
        pass
    return ""


def _ingest_pdf(notebook_id: str) -> str:
    print("  Uploading PDF — this may take 30-120 seconds...")
    result = _upload_pdf(notebook_id, FILING_PDF)
    doc_id = result.get("document_id") or ""
    if not doc_id:
        print(f"ERROR: No document_id in ingest response: {result}", file=sys.stderr)
        sys.exit(1)
    print(f"  Ingested document_id: {doc_id}")
    return doc_id


def _generate_and_write_wiki(notebook_id: str) -> None:
    print("  Starting wiki generation...")
    job = _api_post_empty(f"/notebooks/{notebook_id}/wiki/generate")
    job_id = job["job_id"]
    print(f"  Wiki job: {job_id}")
    max_polls = 240  # 20 min at 5s/poll
    while True:
        max_polls -= 1
        if max_polls <= 0:
            print("ERROR: Wiki generation timed out after 20 minutes", file=sys.stderr)
            sys.exit(1)
        status = _api_get(f"/notebooks/{notebook_id}/wiki/jobs/{job_id}")
        state = status.get("status", "unknown")
        pages_done = status.get("pages_done", 0)
        pages_total = status.get("pages_total", 0)
        print(f"  Wiki: {state} ({pages_done}/{pages_total} pages)")
        if state == "completed":
            break
        if state == "failed":
            print(f"ERROR: Wiki generation failed: {status.get('error')}", file=sys.stderr)
            sys.exit(1)
        time.sleep(5)
    wiki = _api_get(f"/notebooks/{notebook_id}/wiki")
    structure = wiki.get("structure", {})
    pages = wiki.get("pages", [])
    # Backend sections have shape {id, title, page_slugs: [str]}; frontend WikiStructure
    # expects {title, pages: [{slug, title}]}. Join them here so the snapshot is
    # directly consumable by WikiPreviewPanel without transformation at render time.
    pages_by_slug = {p["slug"]: {"slug": p["slug"], "title": p["title"]} for p in pages}
    pages_content_by_slug = {p["slug"]: p["content"] for p in pages}
    transformed_sections = [
        {
            "title": sec["title"],
            "pages": [pages_by_slug[s] for s in sec.get("page_slugs", []) if s in pages_by_slug],
        }
        for sec in structure.get("sections", [])
    ]
    # Use the slug of the first page in the first section so title and content align.
    # (list_pages orders by importance DESC — its page[0] may differ from section[0].pages[0].)
    first_slug = (
        transformed_sections[0]["pages"][0]["slug"]
        if transformed_sections and transformed_sections[0]["pages"]
        else None
    )
    first_page_content = (pages_content_by_slug.get(first_slug) or "") if first_slug else ""
    snapshot = {
        "title": structure.get("title", "Demo Wiki"),
        "sections": transformed_sections,
        "first_page_content": first_page_content,
    }
    WIKI_JSON.parent.mkdir(parents=True, exist_ok=True)
    WIKI_JSON.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Wrote: {WIKI_JSON}")


def _write_qa_snapshot(notebook_id: str) -> None:
    print("  Asking demo question...")
    result = _api_post_json("/ask", {"question": DEMO_QUESTION, "notebook_id": notebook_id})
    QA_JSON.parent.mkdir(parents=True, exist_ok=True)
    QA_JSON.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Wrote: {QA_JSON}")


def _copy_figure_snapshot(doc_id: str) -> None:
    figures_json = FIGURES_BASE / doc_id / "figures.json"
    if not figures_json.exists():
        print(f"  WARNING: No figures.json at {figures_json} — placeholder PNG retained")
        return
    with open(figures_json) as f:
        figures = json.load(f)
    if not figures:
        print("  WARNING: figures.json is empty — placeholder PNG retained")
        return
    src = Path(figures[0]["asset_path"])
    if not src.exists():
        print(f"  WARNING: Figure file not found: {src} — placeholder PNG retained")
        return
    FIGURE_PNG.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, FIGURE_PNG)
    print(f"  Copied: {src} → {FIGURE_PNG}")


def main() -> None:
    print("=== DocQuery Demo Corpus Setup ===\n")

    print("Step 1: Demo notebook")
    notebook_id = _get_or_create_notebook()

    if WIKI_JSON.exists() and QA_JSON.exists() and _figure_is_real():
        print("\nAll output files already exist — nothing to regenerate.")
        print(f"\nDEMO_NOTEBOOK_ID={notebook_id}")
        return

    print("\nStep 2: Download filing PDF")
    _download_filing()

    print("\nStep 3: Ingest PDF into notebook")
    doc_id = _get_existing_doc_id(notebook_id) or _ingest_pdf(notebook_id)

    print("\nStep 4: Generate wiki")
    _generate_and_write_wiki(notebook_id)

    print("\nStep 5: Capture example Q&A")
    _write_qa_snapshot(notebook_id)

    print("\nStep 6: Copy first figure")
    _copy_figure_snapshot(doc_id)

    print(f"\n=== Done ===\n")
    print(f"DEMO_NOTEBOOK_ID={notebook_id}")


if __name__ == "__main__":
    main()
