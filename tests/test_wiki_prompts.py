from apps.api.services.wiki_xml_parser import WikiPageSpec
from apps.api.services.wiki_prompts import build_structure_prompt, build_page_prompt


def test_build_structure_prompt_contains_doc_ids():
    manifest = [
        {"document_id": "doc-abc", "source_file": "report.pdf", "page_count": 10},
        {"document_id": "doc-xyz", "source_file": "policy.pdf", "page_count": 5},
    ]
    prompt = build_structure_prompt(manifest)
    assert "doc-abc" in prompt
    assert "doc-xyz" in prompt
    assert "<wiki_structure>" in prompt
    assert "file_path" in prompt


def test_build_structure_prompt_returns_non_empty_string():
    prompt = build_structure_prompt([{"document_id": "d1", "source_file": "f.pdf"}])
    assert len(prompt) > 100


def test_build_page_prompt_contains_title_and_context():
    page = WikiPageSpec(
        slug="architecture", title="System Architecture",
        description="How components fit together", importance="high", source_doc_ids=["d1"]
    )
    prompt = build_page_prompt(page, "chunk text goes here")
    assert "System Architecture" in prompt
    assert "chunk text goes here" in prompt
    assert "graph TD" in prompt  # Mermaid rules included
    assert "sequenceDiagram" in prompt


def test_build_page_prompt_returns_non_empty_string():
    page = WikiPageSpec(slug="p", title="T", description="D", importance="low", source_doc_ids=[])
    prompt = build_page_prompt(page, "context")
    assert len(prompt) > 100
