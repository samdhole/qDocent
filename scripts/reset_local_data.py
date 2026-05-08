"""Delete all documents from local R2R instance and clear report files."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from r2r import R2RClient

load_dotenv()

BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")


def main() -> None:
    answer = input("Delete ALL documents from R2R and clear reports? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        return

    client = R2RClient(base_url=BASE_URL)

    print("Listing documents ...")
    try:
        docs = client.documents.list()
        doc_list = docs.results if hasattr(docs, "results") else []
    except Exception as exc:
        sys.exit(f"Could not list documents: {exc}\nIs R2R running? make r2r")

    print(f"Deleting {len(doc_list)} document(s) ...")
    for doc in doc_list:
        doc_id = getattr(doc, "id", None) or (doc.get("id") if isinstance(doc, dict) else None)
        print(f"  Deleting {doc_id} ...", end=" ", flush=True)
        try:
            client.documents.delete(id=doc_id)
            print("OK")
        except Exception as exc:
            print(f"FAILED: {exc}")

    for f in Path("reports/evals").glob("*.csv"):
        f.unlink()
        print(f"Removed {f}")
    for f in Path("reports/evals").glob("*.md"):
        f.unlink()
        print(f"Removed {f}")

    print("Reset complete.")


if __name__ == "__main__":
    main()
