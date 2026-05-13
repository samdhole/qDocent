# pattern: Functional Core
from __future__ import annotations

import defusedxml.ElementTree as ET  # prevents XML bomb / XXE on LLM output
from dataclasses import dataclass, field


@dataclass
class WikiPageSpec:
    slug: str                          # derived from page id attribute in XML (e.g., "page-1" → "page-1")
    title: str
    description: str
    importance: str                    # high | medium | low
    source_doc_ids: list[str]          # DocQuery document IDs (from <file_path> / adapted from relevant_files)
    related_slugs: list[str] = field(default_factory=list)


@dataclass
class WikiSection:
    id: str
    title: str
    page_slugs: list[str]              # page id attrs belonging to this section


@dataclass
class WikiStructure:
    title: str
    description: str
    pages: list[WikiPageSpec]
    sections: list[WikiSection] = field(default_factory=list)


def _fallback_structure(reason: str = "") -> WikiStructure:
    """Return a single-page fallback WikiStructure when XML is malformed."""
    overview = WikiPageSpec(
        slug="overview",
        title="Overview",
        description="Auto-generated overview page (XML parsing failed).",
        importance="high",
        source_doc_ids=[],
    )
    return WikiStructure(title="Wiki", description=reason, pages=[overview])


def parse_wiki_structure_xml(xml: str) -> WikiStructure:
    """Parse deepwiki-open-style XML into WikiStructure.

    Returns a fallback WikiStructure (one 'Overview' page) on any parse failure.
    The XML may arrive with or without markdown fences; strip them first.
    """
    # Strip markdown fences if present
    text = xml.strip()
    if "```" in text:
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    # Extract <wiki_structure>...</wiki_structure> block
    start = text.find("<wiki_structure>")
    end = text.find("</wiki_structure>")
    if start == -1 or end == -1:
        return _fallback_structure("No <wiki_structure> block found in LLM output")
    text = text[start: end + len("</wiki_structure>")]

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return _fallback_structure(f"XML parse error: {exc}")

    title = (root.findtext("title") or "Wiki").strip()
    description = (root.findtext("description") or "").strip()

    # Parse pages
    pages: list[WikiPageSpec] = []
    seen_slugs: set[str] = set()
    for page_el in root.findall(".//page"):
        page_id = page_el.get("id", f"page-{len(pages) + 1}")
        # Skip duplicate slugs, preserving order of first occurrence
        if page_id in seen_slugs:
            continue
        seen_slugs.add(page_id)
        page_title = (page_el.findtext("title") or "Untitled").strip()
        page_desc = (page_el.findtext("description") or "").strip()
        importance = (page_el.findtext("importance") or "medium").strip()
        source_doc_ids = [
            fp.text.strip()
            for fp in page_el.findall(".//file_path")
            if fp.text and fp.text.strip()
        ]
        related_slugs = [
            r.text.strip()
            for r in page_el.findall(".//related")
            if r.text and r.text.strip()
        ]
        pages.append(WikiPageSpec(
            slug=page_id,
            title=page_title,
            description=page_desc,
            importance=importance,
            source_doc_ids=source_doc_ids,
            related_slugs=related_slugs,
        ))

    if not pages:
        return _fallback_structure("XML parsed but contained no <page> elements")

    # Parse sections
    sections: list[WikiSection] = []
    for sec_el in root.findall(".//section"):
        sec_id = sec_el.get("id", f"section-{len(sections) + 1}")
        sec_title = (sec_el.findtext("title") or "Section").strip()
        page_refs = [
            pr.text.strip()
            for pr in sec_el.findall("pages/page_ref")
            if pr.text and pr.text.strip()
        ]
        sections.append(WikiSection(id=sec_id, title=sec_title, page_slugs=page_refs))

    return WikiStructure(title=title, description=description, pages=pages, sections=sections)
