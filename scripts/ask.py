"""CLI: ask a RAG question directly against R2R."""
# pattern: Imperative Shell
import os
import sys

from dotenv import load_dotenv
from r2r import R2RClient

load_dotenv()

BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/ask.py \"Your question here\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    client = R2RClient(base_url=BASE_URL)

    print(f"Query: {query}\n")
    try:
        response = client.retrieval.rag(
            query=query,
            search_settings={"limit": 5, "graph_settings": {"enabled": False}},
        )
    except Exception as exc:
        sys.exit(f"RAG query failed: {exc}\nIs R2R running? make r2r")

    # Print answer
    answer = getattr(response, "generated_answer", None) or str(response)
    print("Answer:", answer)

    # Print citations if available
    results = getattr(response, "search_results", None)
    if results:
        print("\nRetrieved chunks:")
        for r in results[:3]:
            score = getattr(r, "score", None)
            score_str = f"{score:.3f}" if isinstance(score, (int, float)) else "?"
            print(f"  score={score_str}  {str(r)[:120]}")


if __name__ == "__main__":
    main()
