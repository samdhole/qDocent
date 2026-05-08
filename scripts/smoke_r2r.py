"""Smoke test: connect to R2R, ingest one PDF, ask one RAG question."""
# pattern: Imperative Shell
import os
import sys
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
    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
