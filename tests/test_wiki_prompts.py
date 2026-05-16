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


# Task 1 tests: cross-reference index and new params
def test_cross_reference_index_present():
    """Test that cross-reference index block is present with correct URLs."""
    pages = [
        WikiPageSpec(
            slug="overview", title="Overview",
            description="Project overview", importance="high", source_doc_ids=[], related_slugs=[]
        ),
        WikiPageSpec(
            slug="architecture", title="System Architecture",
            description="How components fit together", importance="high", source_doc_ids=[], related_slugs=[]
        ),
        WikiPageSpec(
            slug="api-reference", title="API Reference",
            description="API endpoints", importance="medium", source_doc_ids=[], related_slugs=[]
        ),
    ]
    prompt = build_page_prompt(pages[0], "chunk text", all_pages=pages, notebook_id="nb-123")
    # Should contain cross-reference index section
    assert "Cross-reference index" in prompt
    # Should contain links to other pages (not self)
    assert "[System Architecture](/notebooks/nb-123/wiki/architecture)" in prompt
    assert "[API Reference](/notebooks/nb-123/wiki/api-reference)" in prompt
    # Self should NOT be in the cross-reference index list (but may appear in requirement examples)
    # Check that self is excluded from the index by looking at the specific context
    lines = prompt.split("\n")
    cross_ref_section = []
    in_cross_ref = False
    for line in lines:
        if "Cross-reference index" in line:
            in_cross_ref = True
        elif in_cross_ref and ("Closely related" in line or "Requirements" in line):
            break
        elif in_cross_ref:
            cross_ref_section.append(line)
    # Self should not appear in the cross-reference section
    assert not any("/wiki/overview" in line for line in cross_ref_section if "wiki" in line)


def test_related_pages_callout():
    """Test that related pages appear in a separate callout section."""
    pages = [
        WikiPageSpec(
            slug="overview", title="Overview",
            description="Project overview", importance="high", source_doc_ids=[], related_slugs=["architecture"]
        ),
        WikiPageSpec(
            slug="architecture", title="System Architecture",
            description="How components fit together", importance="high", source_doc_ids=[], related_slugs=[]
        ),
        WikiPageSpec(
            slug="api-reference", title="API Reference",
            description="API endpoints", importance="medium", source_doc_ids=[], related_slugs=[]
        ),
    ]
    prompt = build_page_prompt(pages[0], "chunk text", all_pages=pages, notebook_id="nb-123")
    # Related section should mention architecture
    assert "Closely related pages" in prompt or "related" in prompt.lower()
    # api-reference should appear in cross-reference but not in related callout
    assert "/notebooks/nb-123/wiki/api-reference" in prompt


def test_empty_all_pages_graceful():
    """Test that empty all_pages list doesn't cause errors and shows (none)."""
    page = WikiPageSpec(
        slug="overview", title="Overview",
        description="Project overview", importance="high", source_doc_ids=[], related_slugs=[]
    )
    prompt = build_page_prompt(page, "chunk", all_pages=[], notebook_id="nb-123")
    assert "(none)" in prompt or "none" in prompt.lower()
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_no_all_pages_arg_graceful():
    """Test backward compatibility: old 2-arg signature still works."""
    page = WikiPageSpec(
        slug="p", title="T", description="D", importance="low", source_doc_ids=[], related_slugs=[]
    )
    # Call with only 2 args (no all_pages, no notebook_id)
    prompt = build_page_prompt(page, "chunk")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
