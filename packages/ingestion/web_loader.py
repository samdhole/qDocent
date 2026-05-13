# pattern: Imperative Shell
"""Fetch a web URL and convert its content to page dicts using crawl4ai.

Page dicts match the shape produced by parse_pdf.py so all downstream
chunking works without modification. Bboxes are synthetic.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

log = logging.getLogger(__name__)

_SYNTHETIC_PAGE_BBOX = [0.0, 0.0, 612.0, 792.0]
_SECTION_SPLIT_RE = re.compile(r"^#{1,3} ", re.MULTILINE)


def load_url(url: str) -> list[dict[str, Any]]:
    """Fetch a URL and convert its markdown to a list of page dicts.

    Raises RuntimeError if crawl4ai fails or returns empty content.
    """
    markdown = _fetch_url_markdown(url)
    if not markdown.strip():
        raise RuntimeError(f"crawl4ai returned empty content for '{url}'")
    return _markdown_to_pages(markdown)


def _fetch_url_markdown(url: str) -> str:
    """Synchronous wrapper around the async crawl4ai call."""
    try:
        return asyncio.run(_async_fetch(url))
    except RuntimeError as exc:
        # asyncio.run raises RuntimeError if an event loop is already running
        # (e.g. inside Jupyter). Fall back to nest_asyncio or a thread executor.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, _async_fetch(url))
            return future.result()


async def _async_fetch(url: str) -> str:
    from crawl4ai import AsyncWebCrawler  # lazy import

    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url, word_count_threshold=10)
    if not getattr(result, "success", True):
        raise RuntimeError(f"crawl4ai failed for '{url}': {getattr(result, 'error_message', 'unknown error')}")
    return getattr(result, "markdown", "") or ""


def _markdown_to_pages(markdown: str) -> list[dict[str, Any]]:
    """Split markdown on H1–H3 headings; each section becomes a page dict."""
    # Split on headings, keeping the heading text
    parts = _SECTION_SPLIT_RE.split(markdown)
    heading_matches = list(_SECTION_SPLIT_RE.finditer(markdown))

    pages = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        pages.append({
            "page_number": len(pages) + 1,
            "text": part,
            "tables": [],
            "confidence": 100.0,
            "bbox": list(_SYNTHETIC_PAGE_BBOX),
            "text_lines": [],
            "parser": "web",
        })

    if not pages:
        pages.append({
            "page_number": 1,
            "text": markdown.strip(),
            "tables": [],
            "confidence": 100.0,
            "bbox": list(_SYNTHETIC_PAGE_BBOX),
            "text_lines": [],
            "parser": "web",
        })

    return pages
