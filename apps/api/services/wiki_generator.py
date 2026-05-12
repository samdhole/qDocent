# pattern: Imperative Shell
from __future__ import annotations

import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from apps.api.services import notebook_store, r2r_client, wiki_store
from apps.api.services.wiki_prompts import build_page_prompt, build_structure_prompt
from apps.api.services.wiki_xml_parser import WikiPageSpec, WikiStructure, parse_wiki_structure_xml

log = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-3-flash-preview"
_DOCS_BASE_PATH = Path("data/documents")
_MAX_WORKERS = 4


def _make_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=_GEMINI_MODEL, temperature=0)


def _build_doc_manifest(notebook_id: str) -> list[dict]:
    """Build a list of {document_id, source_file, page_count} for all docs in the notebook."""
    docs = notebook_store.list_documents(notebook_id)
    manifest = []
    for doc in docs:
        doc_id = doc["document_id"]
        entry: dict = {"document_id": doc_id, "source_file": doc_id, "page_count": None}
        # Try to enrich with manifest.json data
        manifest_path = _DOCS_BASE_PATH / doc_id / "manifest.json"
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text())
                entry["source_file"] = data.get("source_file", doc_id)
            except Exception:
                pass
        manifest.append(entry)
    return manifest


def _generate_page_content(
    page: WikiPageSpec,
    notebook_id: str,
    r2r_collection_id: str,
    job_id: str,
) -> None:
    """Retrieve chunks for one page, call Gemini, store the result. Called in thread pool.

    Uses r2r_client.rag_query (no conversation memory needed) — page generation is a
    one-shot retrieval. When the page declares source_doc_ids, scope by document IDs;
    otherwise fall back to the notebook's R2R collection scope.
    """
    try:
        # Retrieve relevant chunks from R2R using source_doc_ids or collection_id
        retrieval_result = r2r_client.rag_query(
            query=f"Explain: {page.title}. {page.description}",
            document_ids=page.source_doc_ids if page.source_doc_ids else None,
            collection_id=r2r_collection_id if not page.source_doc_ids else None,
        )
        chunk_texts = [ctx.get("text", "") for ctx in retrieval_result.get("retrieved_contexts", [])]
        chunk_context = "\n\n".join(chunk_texts) if chunk_texts else "(No source material retrieved)"

        # Generate page markdown via Gemini
        prompt = build_page_prompt(page, chunk_context)
        llm = _make_llm()
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Store the generated content
        wiki_store.update_page_content(notebook_id, page.slug, content)
        log.info("Generated page '%s' for notebook %s", page.slug, notebook_id)

    except Exception as exc:
        log.error("Failed to generate page '%s': %s", page.slug, exc)
        wiki_store.update_page_content(
            notebook_id, page.slug,
            f"# {page.title}\n\n*Error generating this page: {exc}*"
        )

    # Atomically increment pages_done counter regardless of success/failure.
    # Avoids races where two parallel page workers both read pages_done=N and
    # both write pages_done=N+1, losing one increment.
    wiki_store.increment_pages_done(job_id)


def generate_wiki(notebook_id: str, r2r_collection_id: str, job_id: str) -> None:
    """Full two-step wiki generation pipeline. Designed to run as a FastAPI BackgroundTask.

    Step 1: Generate XML structure via one Gemini call.
    Step 2: Generate N page contents in parallel via ThreadPoolExecutor.
    Updates wiki_jobs throughout for progress polling.
    """
    try:
        # ── Step 1: Structure ────────────────────────────────────────────────
        wiki_store.update_job(job_id, status="running")

        doc_manifest = _build_doc_manifest(notebook_id)
        if not doc_manifest:
            wiki_store.update_job(job_id, status="failed", error="No documents in notebook")
            return

        prompt = build_structure_prompt(doc_manifest)
        llm = _make_llm()
        structure_response = llm.invoke(prompt)
        raw_xml = structure_response.content if hasattr(structure_response, "content") else str(structure_response)

        structure: WikiStructure = parse_wiki_structure_xml(raw_xml)

        # Store structure + empty page rows
        sections_data = [
            {"id": sec.id, "title": sec.title, "page_slugs": sec.page_slugs}
            for sec in structure.sections
        ]
        wiki_store.store_structure(notebook_id, structure.title, structure.description, sections_data)

        for page in structure.pages:
            wiki_store.upsert_page(
                notebook_id=notebook_id,
                slug=page.slug,
                title=page.title,
                description=page.description,
                importance=page.importance,
                source_doc_ids=page.source_doc_ids,
                related_slugs=page.related_slugs,
                content=None,  # will be filled in Step 2
            )

        wiki_store.update_job(job_id, pages_total=len(structure.pages))

        # ── Step 2: Parallel page generation ────────────────────────────────
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    _generate_page_content, page, notebook_id, r2r_collection_id, job_id
                ): page.slug
                for page in structure.pages
            }
            for future in as_completed(futures):
                slug = futures[future]
                exc = future.exception()
                if exc:
                    log.error("Page generation thread failed for '%s': %s", slug, exc)

        wiki_store.update_job(job_id, status="completed")
        log.info("Wiki generation complete for notebook %s", notebook_id)

    except Exception as exc:
        log.error("Wiki generation failed for notebook %s: %s", notebook_id, exc)
        wiki_store.update_job(job_id, status="failed", error=str(exc))
