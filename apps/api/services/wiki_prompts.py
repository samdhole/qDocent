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

    doc_manifest entries: {document_id: str, source_file: str, page_count: int | None}
    """
    doc_lines = "\n".join(
        f"- ID: {doc['document_id']}  |  File: {doc.get('source_file', 'unknown')}  "
        f"|  Pages: {doc.get('page_count', 'unknown')}"
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


def build_page_prompt(page: WikiPageSpec, chunk_context: str) -> str:
    """Build the LLM prompt to generate a single wiki page in Markdown.

    chunk_context: retrieved text chunks joined by double newline.
    """
    return (
        f"You are an expert technical writer.\n"
        f"Write a comprehensive wiki page in Markdown about: **{page.title}**\n\n"
        f"Page description: {page.description}\n\n"
        f"Source material retrieved from the document corpus:\n"
        f"<source_material>\n{chunk_context}\n</source_material>\n\n"
        f"Requirements for this page:\n"
        f"1. Start with a H1 heading: # {page.title}\n"
        f"2. Use H2 (##) and H3 (###) headings to organize content\n"
        f"3. {_MERMAID_RULES}\n"
        f"4. Include at least one Mermaid diagram if the content has structural relationships\n"
        f"5. Use Markdown tables to summarize key information\n"
        f"6. Ground every claim in the provided source material\n"
        f"7. Write clear, professional technical prose\n"
        f"8. End with a brief summary paragraph\n\n"
        f"Generate ONLY the Markdown content for this page."
    )
