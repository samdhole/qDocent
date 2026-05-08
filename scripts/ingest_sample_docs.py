"""Ingest all sample PDFs into R2R."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from r2r import R2RClient

load_dotenv()

SAMPLE_DIR = Path("data/sample_docs")
BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")


def main() -> None:
    pdfs = sorted(SAMPLE_DIR.glob("*.pdf"))
    if not pdfs:
        sys.exit(
            f"No PDFs found in {SAMPLE_DIR}. "
            "Run: uv run python scripts/create_sample_docs.py"
        )

    client = R2RClient(base_url=BASE_URL)
    print(f"Ingesting {len(pdfs)} document(s) into {BASE_URL} ...")

    failures = []
    for pdf in pdfs:
        print(f"  {pdf.name} ...", end=" ", flush=True)
        try:
            _ = client.documents.create(file_path=str(pdf))
            print("OK")
        except Exception as exc:
            print(f"FAILED: {exc}")
            failures.append((pdf.name, str(exc)))

    if failures:
        print(f"\n{len(failures)} ingestion(s) failed.")
        # Check if it's a connection error
        if failures and "Connection" in failures[0][1]:
            sys.exit("Is R2R running? Start it with: make r2r")
        else:
            sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
