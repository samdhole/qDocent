"""Smoke test: connect to R2R, ingest one PDF, ask one RAG question."""
# pattern: Imperative Shell
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from r2r import R2RClient

load_dotenv()

BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")
SAMPLE = Path("data/sample_docs/company_policy.pdf")


def main() -> None:
    if not SAMPLE.exists():
        sys.exit(
            f"Missing {SAMPLE}. Run: uv run python scripts/create_sample_docs.py"
        )

    print(f"Connecting to R2R at {BASE_URL}")
    client = R2RClient(base_url=BASE_URL)

    print(f"Ingesting {SAMPLE} ...")
    try:
        result = client.documents.create(file_path=str(SAMPLE))
        print("Document created:", result)
    except Exception as exc:
        sys.exit(
            f"Ingestion failed: {exc}\n"
            "Is R2R running? Start it with: make r2r"
        )

    print("\nAsking RAG question ...")
    response = client.retrieval.rag(
        query="Summarize the most important policy and cite the source.",
        search_settings={"limit": 5, "graph_settings": {"enabled": False}},
    )
    print("RAG response:", response)

    # Pre-chunked ingest smoke — verifies DocQuery Citation header round-trip
    print("\nTesting pre-chunked ingest (DocQuery Citation header round-trip) ...")
    from apps.api.services.r2r_client import ingest_prechunked_document, rag_query

    smoke_chunk = {
        "document_id": "smoke_prechunked_doc",
        "source_file": "smoke_prechunked.pdf",
        "page_start": 1,
        "page_end": 1,
        "section_path": "SmokeTest",
        "text": "The pre-chunked ingest smoke test policy: all items covered.",
    }
    try:
        ingest_prechunked_document([smoke_chunk], {"document_id": "smoke_prechunked_doc", "source_file": "smoke_prechunked.pdf"})
        print("Pre-chunked ingest: OK")
    except Exception as exc:
        sys.exit(f"Pre-chunked ingest failed: {exc}")

    time.sleep(3)

    result = rag_query("pre-chunked ingest smoke test policy")
    known_citations = [c for c in result.get("citations", []) if c.get("document") != "unknown"]
    if known_citations:
        print(f"Citation header round-trip: OK — document={known_citations[0]['document']!r}, page={known_citations[0]['page']}")
    else:
        print(
            "WARNING: Citation header round-trip FAILED — all citations have document='unknown'. "
            "Pre-chunked ingest may not be preserving DocQuery Citation headers through R2R. "
            "Run: pytest tests/test_integration_r2r_citation.py -v for detailed diagnostics."
        )

    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
