# pattern: Functional Core
from __future__ import annotations

from apps.api.services.wiki_xml_parser import WikiPageSpec

_MERMAID_RULES = """\
When creating diagrams, follow these CRITICAL rules:
- Use "graph TD" (top-down) for flow/architecture diagrams — NEVER "graph LR"
- Maximum node width: 3–4 words
- For sequence diagrams start with "sequenceDiagram" on its own line, define ALL participants first
- Use correct Mermaid arrow syntax:
  ->> solid with arrowhead (requests/calls)  -->> dotted with arrowhead (responses)
  ->x solid with X (error)   -) solid open arrow (async)
- NEVER use flowchart-style labels A--|label|-->B; always use A->>B: My Label
- For classDiagram use standard UML notation
- Supported directives: graph TD, sequenceDiagram, classDiagram, erDiagram, flowchart TD"""

_STRUCTURE_XML_SCHEMA = """\
Return ONLY valid XML matching this schema (no markdown fences, no preamble):

<wiki_structure>
  <title>[Wiki title]</title>
  <description>[Brief description of the document corpus]</description>
  <sections>
    <section id="section-1">
      <title>[Section title]</title>
      <pages>
        <page_ref>page-1</page_ref>
      </pages>
    </section>
  </sections>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[What this page covers]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[docquery_document_id]</file_path>
      </relevant_files>
      <related_pages>
        <related>page-2</related>
      </related_pages>
    </page>
  </pages>
</wiki_structure>

IMPORTANT:
- Start directly with <wiki_structure>, end with </wiki_structure>
- file_path elements must contain docquery_document_id values from the document list above
- Create 4-10 pages covering distinct aspects of the document corpus
- Return ONLY valid XML — no text before or after"""


def build_structure_prompt(doc_manifest: list[dict]) -> str:
    """Build the LLM prompt to generate wiki XML structure from a document manifest.

    doc_manifest entries: {document_id: str, source_file: str}
    """
    doc_lines = "\n".join(
        f"- ID: {doc['document_id']}  |  File: {doc.get('source_file', 'unknown')}"
        for doc in doc_manifest
    )
    return (
        f"You are an expert technical writer.\n"
        f"Analyze this document corpus and design a comprehensive wiki structure.\n\n"
        f"Document corpus ({len(doc_manifest)} documents):\n{doc_lines}\n\n"
        f"Design a wiki with sections and pages that covers the key topics in these documents.\n"
        f"Each page's <file_path> elements must reference document IDs from the list above.\n\n"
        f"{_STRUCTURE_XML_SCHEMA}"
    )


def build_page_prompt(
    page: WikiPageSpec,
    chunk_context: str,
    all_pages: list[WikiPageSpec] | None = None,
    notebook_id: str = "",
) -> str:
    """Build the LLM prompt to generate a single wiki page in Markdown.

    page: WikiPageSpec for the page to generate.
    chunk_context: retrieved text chunks joined by double newline.
    all_pages: list of all pages in the wiki structure (optional, for cross-reference index).
    notebook_id: notebook ID for constructing wiki page URLs (optional).
    """
    # Build cross-reference index
    cross_ref_lines = []
    related_lines = []
    if all_pages and notebook_id:
        related_set = set(page.related_slugs)
        for p in all_pages:
            if p.slug == page.slug:
                continue  # skip self
            url = f"/notebooks/{notebook_id}/wiki/{p.slug}"
            line = f"- [{p.title}]({url})"
            cross_ref_lines.append(line)
            # Identify related pages for prominent callout
            if p.slug in related_set:
                related_lines.append(line)

    # Build cross-reference section
    cross_ref_section = ""
    if all_pages is not None and notebook_id:
        cross_ref_section = (
            f"Cross-reference index (other wiki pages you may link to):\n"
            f"{chr(10).join(cross_ref_lines) if cross_ref_lines else '(none)'}\n\n"
            f"Closely related pages (prefer linking to these when relevant):\n"
            f"{chr(10).join(related_lines) if related_lines else '(none — link to any page above)'}\n\n"
        )
    elif all_pages == []:
        # Graceful empty case
        cross_ref_section = (
            f"Cross-reference index (other wiki pages you may link to):\n"
            f"(none)\n\n"
            f"Closely related pages (prefer linking to these when relevant):\n"
            f"(none — link to any page above)\n\n"
        )

    # Build conditional linking rules based on whether notebook_id is provided
    linking_rules = ""
    if notebook_id:
        linking_rules = (
            f"7. When you reference a topic covered by another wiki page, use a Markdown link from the cross-reference index above — e.g. [Overview](/notebooks/{notebook_id}/wiki/overview)\n"
            f"8. Do NOT invent URLs — only link to pages listed in the cross-reference index\n"
            f"9. Write clear, professional technical prose\n"
            f"10. End with a brief summary paragraph\n\n"
        )
    else:
        linking_rules = (
            f"7. Write clear, professional technical prose\n"
            f"8. End with a brief summary paragraph\n\n"
        )

    return (
        f"You are an expert technical writer.\n"
        f"Write a comprehensive wiki page in Markdown about: **{page.title}**\n\n"
        f"Page description: {page.description}\n\n"
        f"Source material retrieved from the document corpus:\n"
        f"<source_material>\n{chunk_context}\n</source_material>\n\n"
        f"{cross_ref_section}"
        f"Requirements for this page:\n"
        f"1. Start with a H1 heading: # {page.title}\n"
        f"2. Use H2 (##) and H3 (###) headings to organize content\n"
        f"3. {_MERMAID_RULES}\n"
        f"4. Include at least one Mermaid diagram if the content has structural relationships\n"
        f"5. Use Markdown tables to summarize key information\n"
        f"6. Ground every claim in the provided source material\n"
        + linking_rules
        + f"Generate ONLY the Markdown content for this page."
    )
