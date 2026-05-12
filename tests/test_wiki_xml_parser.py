import pytest
from apps.api.services.wiki_xml_parser import parse_wiki_structure_xml


VALID_XML = """
<wiki_structure>
  <title>My Wiki</title>
  <description>A test wiki</description>
  <sections>
    <section id="section-1">
      <title>Core</title>
      <pages>
        <page_ref>page-1</page_ref>
      </pages>
    </section>
  </sections>
  <pages>
    <page id="page-1">
      <title>Overview</title>
      <description>The big picture</description>
      <importance>high</importance>
      <relevant_files>
        <file_path>doc-abc123</file_path>
      </relevant_files>
      <related_pages><related>page-2</related></related_pages>
    </page>
    <page id="page-2">
      <title>Architecture</title>
      <description>How it fits together</description>
      <importance>medium</importance>
      <relevant_files/>
      <related_pages/>
    </page>
  </pages>
</wiki_structure>
"""


def test_parses_valid_xml():
    structure = parse_wiki_structure_xml(VALID_XML)
    assert structure.title == "My Wiki"
    assert structure.description == "A test wiki"
    assert len(structure.pages) == 2
    assert structure.pages[0].slug == "page-1"
    assert structure.pages[0].title == "Overview"
    assert structure.pages[0].importance == "high"
    assert structure.pages[0].source_doc_ids == ["doc-abc123"]
    assert structure.pages[0].related_slugs == ["page-2"]
    assert len(structure.sections) == 1
    assert structure.sections[0].page_slugs == ["page-1"]


def test_strips_markdown_fences():
    wrapped = f"```xml\n{VALID_XML.strip()}\n```"
    structure = parse_wiki_structure_xml(wrapped)
    assert structure.title == "My Wiki"


def test_malformed_xml_returns_fallback():
    structure = parse_wiki_structure_xml("<wiki_structure><title>Oops</title><pages><page id='p1'>")
    assert structure.pages[0].title == "Overview"
    assert len(structure.pages) == 1


def test_truncated_no_wiki_structure_tag_returns_fallback():
    structure = parse_wiki_structure_xml("Here is some text that got cut off")
    assert len(structure.pages) == 1
    assert structure.pages[0].slug == "overview"


def test_xml_with_no_pages_returns_fallback():
    structure = parse_wiki_structure_xml("<wiki_structure><title>T</title><pages/></wiki_structure>")
    assert len(structure.pages) == 1
    assert structure.pages[0].title == "Overview"


def test_does_not_raise_on_any_input():
    # Fuzz: should never raise
    for bad_input in ["", "null", "<broken>", "<?xml?>", "<wiki_structure/>"]:
        result = parse_wiki_structure_xml(bad_input)
        assert result.pages  # always at least one page
