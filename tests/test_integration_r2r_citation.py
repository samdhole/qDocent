"""Integration tests for the pre-chunked ingest citation round-trip.

Skipped unless a live R2R server is reachable at R2R_BASE_URL (default
http://localhost:7272). Run with: pytest tests/test_integration_r2r_citation.py -v
"""
# pattern: Imperative Shell
import os
import time
import uuid

import pytest

R2R_BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")


def _r2r_reachable() -> bool:
    # Probe R2R health endpoint directly with a short timeout to avoid slowing pytest
    # collection when R2R is unreachable. Use httpx.get rather than R2RClient SDK
    # constructor to ensure timeout applies and avoid SDK version issues.
    try:
        import httpx
        health_url = f"{R2R_BASE_URL}/health"
        httpx.get(health_url, timeout=0.5)
        return True
    except Exception:
        return False


skip_if_no_r2r = pytest.mark.skipif(
    not _r2r_reachable(),
    reason=f"R2R not reachable at {R2R_BASE_URL} — start with `make r2r`",
)


@skip_if_no_r2r
def test_prechunked_ingest_citation_round_trip():
    """Ingest one chunk via pre-chunked path; RAG query returns citation with doc != 'unknown'.

    This validates the full DocQuery Citation header round-trip:
    chunk_text_for_r2r() → R2R storage → rag_query() → citation_from_retrieved_text().
    """
    from apps.api.services.r2r_client import ingest_prechunked_document, rag_query, delete_r2r_documents

    # Use unique document ID per run to avoid conflicts with previous test runs
    unique_doc_id = f"smoke_test_doc_{uuid.uuid4().hex[:8]}"
    r2r_document_id = None

    try:
        test_chunk = {
            "document_id": unique_doc_id,
            "source_file": "smoke_test.pdf",
            "page_start": 1,
            "page_end": 1,
            "section_path": "SmokeTest",
            "text": (
                "The smoke test refund policy states that all smoke test purchases are "
                "eligible for a full refund within 30 smoke test days."
            ),
        }
        report = {"document_id": unique_doc_id, "source_file": "smoke_test.pdf"}

        # Ingest the chunk
        ingest_response = ingest_prechunked_document([test_chunk], report)
        # Extract the R2R document ID for cleanup
        # The R2R SDK returns a Pydantic model with .results property, not a dict
        try:
            r2r_document_id = str(ingest_response.results.document_id)
        except AttributeError:
            pass

        # Wait for R2R to index (R2R's background ingestion pipeline takes a moment)
        time.sleep(3)

        # Query — use distinctive text from the chunk to ensure retrieval
        result = rag_query("smoke test refund policy")

        citations = result.get("citations", [])
        assert citations, "Expected at least one citation in the RAG response"

        # Verify that citation headers were parsed — at least one should have document != "unknown"
        known_citations = [c for c in citations if c.get("document") != "unknown"]
        assert known_citations, (
            "All citations have document='unknown'. "
            "This means the DocQuery Citation header was not preserved through R2R storage and retrieval. "
            f"Citations received: {citations}"
        )

        smoke_citation = known_citations[0]
        assert smoke_citation["document"] == "smoke_test.pdf", (
            f"Expected document='smoke_test.pdf', got {smoke_citation['document']!r}"
        )
        assert isinstance(smoke_citation["page"], int), (
            f"Expected page to be an integer, got {type(smoke_citation['page'])}: {smoke_citation['page']!r}"
        )
    finally:
        # Cleanup: delete the test document from the shared R2R instance
        if r2r_document_id:
            delete_r2r_documents([r2r_document_id])
