# pattern: Imperative Shell
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_google_genai import ChatGoogleGenerativeAI

from apps.api.services import notebook_store, r2r_client, wiki_store, document_store
from apps.api.services.wiki_prompts import build_page_prompt, build_structure_prompt
from apps.api.services.wiki_xml_parser import WikiPageSpec, WikiStructure, parse_wiki_structure_xml

log = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-3-flash-preview"
_MAX_WORKERS = 4


def _make_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=_GEMINI_MODEL, temperature=0)


def _build_doc_manifest(notebook_id: str) -> list[dict]:
    """Build a list of {document_id, source_file} for all docs in the notebook."""
    docs = notebook_store.list_documents(notebook_id)
    manifest = []
    for doc in docs:
        doc_id = doc["document_id"]
        # Load persisted metadata or fall back to doc_id as source_file
        persisted = document_store.load_document_manifest(doc_id)
        source_file = persisted.get("source_file", doc_id) if persisted else doc_id
        entry = {"document_id": doc_id, "source_file": source_file}
        manifest.append(entry)
    return manifest


def _valid_doc_ids(page_ids: list[str], manifest_ids: set[str]) -> list[str]:
    """Return only the IDs from page_ids that exist in manifest_ids, preserving order."""
    return [doc_id for doc_id in page_ids if doc_id in manifest_ids]


def _generate_page_content(
    page: WikiPageSpec,
    notebook_id: str,
    r2r_collection_id: str,
    job_id: str,
    all_pages: list[WikiPageSpec],
) -> None:
    """Retrieve chunks for one page, call Gemini, store the result. Called in thread pool.

    Uses r2r_client.rag_query (no conversation memory needed) — page generation is a
    one-shot retrieval. When the page declares source_doc_ids, scope by document IDs;
    otherwise fall back to the notebook's R2R collection scope.

    all_pages: all WikiPageSpec objects in the wiki structure, used for cross-reference index.
    """
    page_log = logging.LoggerAdapter(log, {"job_id": job_id, "notebook_id": notebook_id})
    try:
        # Retrieve relevant chunks — try doc-scoped first, fall back to collection scope
        # if doc-scoped returns nothing (happens when structure XML has wrong/invented doc IDs).
        _query = f"{page.title}. {page.description}"
        retrieval_result = r2r_client.rag_query(
            query=_query,
            document_ids=page.source_doc_ids if page.source_doc_ids else None,
            collection_id=r2r_collection_id if not page.source_doc_ids else None,
        )
        chunk_texts = [ctx.get("text", "") for ctx in retrieval_result.get("retrieved_contexts", [])]

        if not chunk_texts and page.source_doc_ids:
            # Doc-scoped retrieval returned nothing — fall back to full collection
            page_log.warning(
                "Page '%s': doc-scoped retrieval returned no chunks (source_doc_ids=%s); "
                "falling back to collection-scoped retrieval",
                page.slug, page.source_doc_ids,
            )
            retrieval_result = r2r_client.rag_query(
                query=_query,
                collection_id=r2r_collection_id,
            )
            chunk_texts = [ctx.get("text", "") for ctx in retrieval_result.get("retrieved_contexts", [])]

        if not chunk_texts:
            page_log.warning("Page '%s': no chunks retrieved from collection either", page.slug)

        chunk_context = "\n\n".join(chunk_texts) if chunk_texts else "(No source material retrieved)"

        # Generate page markdown via Gemini
        prompt = build_page_prompt(page, chunk_context, all_pages=all_pages, notebook_id=notebook_id)
        llm = _make_llm()
        response = llm.invoke(prompt)
        raw_content = response.content if hasattr(response, "content") else str(response)
        # gemini-3-flash-preview may return content as a list of parts (strings or {text: ...} dicts) — flatten to a single string
        content = (
            "".join(p if isinstance(p, str) else (p.get("text", "") if isinstance(p, dict) else str(p)) for p in raw_content)
            if isinstance(raw_content, list)
            else raw_content
        )

        # Store the generated content
        wiki_store.update_page_content(notebook_id, page.slug, content)
        page_log.info("Generated page '%s'", page.slug)

    except Exception as exc:
        page_log.exception("Failed to generate page '%s'", page.slug)
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

        manifest_ids: set[str] = {entry["document_id"] for entry in doc_manifest}

        prompt = build_structure_prompt(doc_manifest)
        llm = _make_llm()
        structure_response = llm.invoke(prompt)
        raw_content = structure_response.content if hasattr(structure_response, "content") else str(structure_response)
        # gemini-3-flash-preview may return content as a list of parts (strings or {text: ...} dicts) — flatten to a single string
        raw_xml = (
            "".join(p if isinstance(p, str) else (p.get("text", "") if isinstance(p, dict) else str(p)) for p in raw_content)
            if isinstance(raw_content, list)
            else raw_content
        )

        structure: WikiStructure = parse_wiki_structure_xml(raw_xml)

        # Remap each page's source_doc_ids to only IDs that actually exist in this notebook.
        # Prevents hallucinated IDs from the structure LLM call reaching rag_query.
        for page in structure.pages:
            valid = _valid_doc_ids(page.source_doc_ids, manifest_ids)
            if len(valid) < len(page.source_doc_ids):
                dropped = set(page.source_doc_ids) - set(valid)
                log.warning(
                    "Page '%s': dropped %d invented doc ID(s) %s; keeping %s",
                    page.slug, len(dropped), dropped, valid or "(none — will use collection fallback)",
                )
            page.source_doc_ids = valid

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
                    _generate_page_content, page, notebook_id, r2r_collection_id, job_id, structure.pages
                ): page.slug
                for page in structure.pages
            }
            for future in as_completed(futures):
                slug = futures[future]
                exc = future.exception()
                if exc:
                    log.error("Page generation thread failed for '%s'", slug, exc_info=exc)

        wiki_store.update_job(job_id, status="completed")
        log.info("Wiki generation complete for notebook %s", notebook_id)

    except Exception as exc:
        log.exception("Wiki generation failed for notebook %s", notebook_id)
        wiki_store.update_job(job_id, status="failed", error=str(exc))
