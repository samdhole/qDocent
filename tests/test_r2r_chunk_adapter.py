"""Tests for DocQuery chunk text sent to R2R."""

from apps.api.services.r2r_chunk_adapter import (
    chunk_text_for_r2r,
    citation_from_retrieved_text,
)


def test_chunk_text_for_r2r_embeds_citation_header():
    """R2R chunk text contains source/page metadata before the body."""
    chunk = {
        "text": "Refunds are available for 30 days.",
        "document_id": "company_policy",
        "source_file": "company_policy.pdf",
        "page_start": 2,
        "page_end": 3,
        "section_path": "Refunds",
        "bbox": [1, 2, 3, 4],
        "parser": "fast_text",
        "chunk_template": "policy",
        "confidence": 0.98,
    }

    text = chunk_text_for_r2r(chunk, chunk_index=7)

    assert text.startswith(
        "DocQuery Citation: "
        "document_id=company_policy; source_file=company_policy.pdf; "
        "page_start=2; page_end=3; section_path=Refunds; chunk_index=7"
    )
    assert "\n\nRefunds are available for 30 days." in text


def test_citation_from_retrieved_text_parses_header_and_strips_body():
    """Retrieved text with a DocQuery header yields citation metadata and clean body."""
    text = (
        "DocQuery Citation: document_id=company_policy; "
        "source_file=company_policy.pdf; page_start=2; page_end=3; "
        "section_path=Refunds; chunk_index=7\n\n"
        "Refunds are available for 30 days."
    )

    citation, clean_text = citation_from_retrieved_text(text)

    assert citation == {
        "document_id": "company_policy",
        "document": "company_policy.pdf",
        "page": 2,
        "page_end": 3,
        "section": "Refunds",
        "chunk_index": 7,
    }
    assert clean_text == "Refunds are available for 30 days."


def test_citation_from_retrieved_text_falls_back_for_plain_text():
    """Plain R2R chunks remain usable when no DocQuery header is present."""
    citation, clean_text = citation_from_retrieved_text("Plain retrieved text")

    assert citation == {}
    assert clean_text == "Plain retrieved text"


def test_chunk_text_for_r2r_none_fields_produce_empty_string():
    """None values in chunk fields write empty string in header, not the literal 'None'."""
    chunk = {"text": "body", "document_id": None, "source_file": None, "page_start": None}
    text = chunk_text_for_r2r(chunk, chunk_index=0)
    assert "document_id=;" in text
    assert "source_file=;" in text
    assert "page_start=;" in text
    citation, clean = citation_from_retrieved_text(text)
    # Empty values in header decode to empty string, not literal "None" or back to None
    assert citation["document_id"] == ""
    assert citation["document"] == ""  # source_file was None → empty string in header → empty string on decode
    assert citation["page"] is None  # _int_or_none("") returns None
    assert clean == "body"


def test_chunk_text_for_r2r_section_path_with_equals_roundtrips():
    """section_path containing '=' survives encode/decode because split uses maxsplit=1."""
    chunk = {
        "text": "body",
        "document_id": "doc1",
        "source_file": "doc1.pdf",
        "page_start": 1,
        "page_end": 1,
        "section_path": "k=v style heading",
    }
    text = chunk_text_for_r2r(chunk, chunk_index=0)
    citation, _ = citation_from_retrieved_text(text)
    assert citation["section"] == "k=v style heading"


def test_chunk_text_for_r2r_source_file_with_semicolon_encodes_to_comma():
    """';' in source_file is replaced with ',' so it cannot break the header split delimiter."""
    chunk = {
        "text": "body",
        "document_id": "doc1",
        "source_file": "report; final.pdf",
        "page_start": 1,
        "page_end": 1,
        "section_path": "Intro",
    }
    text = chunk_text_for_r2r(chunk, chunk_index=0)
    assert "report, final.pdf" in text  # semicolon replaced
    citation, _ = citation_from_retrieved_text(text)
    assert citation["document"] == "report, final.pdf"
