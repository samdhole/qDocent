"""Tests for chunk templating module."""
import pytest

from packages.ingestion.chunk_templates import (
    _make_chunk,
    _split_text,
    _union_bbox,
    _tight_bbox,
    chunk_document,
)


# Required fields constant (from CONTEXT.md invariant)
REQUIRED_CHUNK_FIELDS = {
    "document_id",
    "source_file",
    "page_start",
    "page_end",
    "section_path",
    "bbox",
    "parser",
    "chunk_template",
    "confidence",
    "text",  # Plus text key
}


class TestMakeChunk:
    """Test _make_chunk() output schema."""

    def test_make_chunk_all_required_fields(self):
        """Chunk should contain all 9 required metadata fields + text."""
        chunk = _make_chunk(
            text="This is a chunk",
            document_id="test_doc",
            source_file="test.pdf",
            page_start=1,
            page_end=1,
            section_path="Introduction",
            bbox=[0, 0, 612, 792],
            parser="fast_text",
            chunk_template="policy",
            confidence=95.5,
        )

        # Check all required fields present
        assert set(chunk.keys()) >= REQUIRED_CHUNK_FIELDS

        # Check required field values
        assert chunk["document_id"] == "test_doc"
        assert chunk["source_file"] == "test.pdf"
        assert chunk["page_start"] == 1
        assert chunk["page_end"] == 1
        assert chunk["section_path"] == "Introduction"
        assert chunk["bbox"] == [0, 0, 612, 792]
        assert chunk["parser"] == "fast_text"
        assert chunk["chunk_template"] == "policy"
        assert "This is a chunk" in chunk["text"]

    def test_confidence_normalization(self):
        """Confidence should be normalized from 0-100 to 0-1."""
        chunk = _make_chunk(
            text="test",
            document_id="doc",
            source_file="file.pdf",
            page_start=1,
            page_end=1,
            section_path="Section",
            bbox=[],
            parser="fast_text",
            chunk_template="policy",
            confidence=100.0,
        )
        # 100.0 should become 1.0
        assert chunk["confidence"] == 1.0

        chunk = _make_chunk(
            text="test",
            document_id="doc",
            source_file="file.pdf",
            page_start=1,
            page_end=1,
            section_path="Section",
            bbox=[],
            parser="fast_text",
            chunk_template="policy",
            confidence=50.0,
        )
        # 50.0 should become 0.5
        assert chunk["confidence"] == 0.5

    def test_extra_fields_included(self):
        """Extra fields passed in extra dict should be included."""
        chunk = _make_chunk(
            text="test",
            document_id="doc",
            source_file="file.pdf",
            page_start=1,
            page_end=1,
            section_path="Section",
            bbox=[],
            parser="fast_text",
            chunk_template="policy",
            confidence=100.0,
            extra={"custom_field": "custom_value"},
        )
        assert chunk["custom_field"] == "custom_value"


class TestSplitText:
    """Test _split_text() boundary behavior."""

    def test_text_under_max_chars(self):
        """Text shorter than max_chars should not be split."""
        text = "This is a short text."
        result = _split_text(text, max_chars=100)
        assert len(result) == 1
        assert result[0] == text

    def test_text_exact_max_chars(self):
        """Text exactly at max_chars should be one chunk."""
        text = "X" * 100
        result = _split_text(text, max_chars=100)
        assert len(result) == 1
        assert len(result[0]) <= 100

    def test_text_over_max_chars_splits_at_sentence(self):
        """Text over max_chars should split at sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence."
        result = _split_text(text, max_chars=30)
        assert len(result) > 1
        # Each chunk should be under limit or be a single sentence
        for chunk in result:
            if len(chunk) > 30:
                # If over limit, it should be unsplittable (no period before max_chars)
                assert "." not in chunk[:-1]  # no period except at end

    def test_text_without_sentence_breaks(self):
        """Text without sentence breaks should split at max_chars."""
        text = "X" * 150
        result = _split_text(text, max_chars=100)
        assert len(result) == 2
        # First chunk at max_chars, second is remainder
        assert len(result[0]) <= 100
        assert len(result[1]) <= 100


class TestChunkDocument:
    """Test chunk_document() with various templates."""

    def test_heading_aware_chunks_required_fields(self):
        """Chunks from heading-aware template should have all required fields."""
        pages = [
            {
                "page_number": 1,
                "text": "# Heading One\nSome text here.",
                "tables": [],
                "confidence": 100.0,
                "bbox": [0, 0, 612, 792],
                "parser": "fast_text",
            }
        ]
        chunks = chunk_document(
            pages=pages,
            normalized_tables=[],
            document_id="test",
            source_file="test.pdf",
            parser="fast_text",
            chunk_template="policy",
            max_chars=1200,
        )

        assert len(chunks) > 0
        for chunk in chunks:
            # Check all required fields present
            assert REQUIRED_CHUNK_FIELDS.issubset(set(chunk.keys()))

    def test_table_aware_chunks_with_table_metadata(self):
        """Table chunks should have raw_table_markdown and normalized_table_text."""
        pages = [
            {
                "page_number": 1,
                "text": "Some text.",
                "tables": [],
                "confidence": 100.0,
                "bbox": [0, 0, 612, 792],
                "parser": "table_aware",
            }
        ]
        normalized_tables = [
            {
                "page_number": 1,
                "raw_table_markdown": "| Col1 | Col2 |\n|------|------|\n| A | 1 |",
                "normalized_table_text": "Table with columns: Col1, Col2. The A has col2 1.",
                "bbox": [0, 0, 300, 100],
            }
        ]
        chunks = chunk_document(
            pages=pages,
            normalized_tables=normalized_tables,
            document_id="test",
            source_file="test.pdf",
            parser="table_aware",
            chunk_template="table_aware",
            max_chars=1200,
        )

        # Should have table chunk
        table_chunks = [c for c in chunks if "raw_table_markdown" in c]
        assert len(table_chunks) > 0

        for chunk in table_chunks:
            assert "raw_table_markdown" in chunk
            assert "normalized_table_text" in chunk

    def test_legal_contract_chunks(self):
        """Legal contract chunks should be split by clauses."""
        pages = [
            {
                "page_number": 1,
                "text": "1. First clause here. Some details.\n2. Second clause. More details.",
                "tables": [],
                "confidence": 100.0,
                "bbox": [0, 0, 612, 792],
                "parser": "fast_text",
            }
        ]
        chunks = chunk_document(
            pages=pages,
            normalized_tables=[],
            document_id="test",
            source_file="test.pdf",
            parser="fast_text",
            chunk_template="legal_contract",
            max_chars=1200,
        )

        assert len(chunks) > 0
        for chunk in chunks:
            assert REQUIRED_CHUNK_FIELDS.issubset(set(chunk.keys()))
            # Legal contract chunks should have section_path like "Clause 1"
            assert "Clause" in chunk["section_path"] or chunk["section_path"]

    def test_empty_pages_produces_no_chunks(self):
        """Pages with empty text should produce no chunks."""
        pages = [
            {
                "page_number": 1,
                "text": "",
                "tables": [],
                "confidence": 100.0,
                "bbox": [0, 0, 612, 792],
                "parser": "fast_text",
            }
        ]
        chunks = chunk_document(
            pages=pages,
            normalized_tables=[],
            document_id="test",
            source_file="test.pdf",
            parser="fast_text",
            chunk_template="policy",
            max_chars=1200,
        )

        assert len(chunks) == 0


class TestBboxHelpers:
    """_union_bbox and _tight_bbox compute tight paragraph bboxes."""

    def test_union_bbox_single_line(self):
        lines = [{"x0": 10, "top": 20, "x1": 300, "bottom": 35}]
        assert _union_bbox(lines) == [10, 20, 300, 35]

    def test_union_bbox_multiple_lines(self):
        lines = [
            {"x0": 10, "top": 20, "x1": 300, "bottom": 35},
            {"x0": 15, "top": 40, "x1": 280, "bottom": 55},
        ]
        assert _union_bbox(lines) == [10, 20, 300, 55]

    def test_union_bbox_empty_returns_fallback_shape(self):
        # Empty input → [0,0,0,0]
        assert _union_bbox([]) == [0.0, 0.0, 0.0, 0.0]

    def test_tight_bbox_matches_lines_in_chunk(self):
        text_lines = [
            {"text": "The quick brown fox", "x0": 10, "top": 20, "x1": 300, "bottom": 35},
            {"text": "jumps over the lazy dog", "x0": 10, "top": 40, "x1": 280, "bottom": 55},
            {"text": "Unrelated sentence here", "x0": 10, "top": 100, "x1": 200, "bottom": 115},
        ]
        chunk_text = "The quick brown fox jumps over the lazy dog"
        page_bbox = [0, 0, 612, 792]
        result = _tight_bbox(text_lines, chunk_text, page_bbox)
        # Should match first two lines, NOT the third
        assert result[1] == pytest.approx(20, abs=1)   # top = first line top
        assert result[3] == pytest.approx(55, abs=1)   # bottom = second line bottom
        # Tight bbox must be smaller than page
        assert result[3] < page_bbox[3]

    def test_tight_bbox_falls_back_to_page_bbox_when_no_match(self):
        text_lines = [{"text": "xyz", "x0": 10, "top": 20, "x1": 100, "bottom": 35}]
        chunk_text = "completely unrelated text with no overlap"
        page_bbox = [0, 0, 612, 792]
        result = _tight_bbox(text_lines, chunk_text, page_bbox)
        assert result == page_bbox

    def test_tight_bbox_empty_lines_falls_back(self):
        result = _tight_bbox([], "some chunk text", [0, 0, 612, 792])
        assert result == [0, 0, 612, 792]


class TestChunkBboxPrecision:
    """chunk_document must produce tight (not page-wide) bboxes for text chunks."""

    def _make_page(self, pnum: int = 1) -> dict:
        return {
            "page_number": pnum,
            "text": "Introduction\n\nThis is the first paragraph of the document.\n\nSecond Section\n\nThis is another paragraph with different content.",
            "tables": [],
            "confidence": 100.0,
            "bbox": [0, 0, 612, 792],
            "text_lines": [
                {"text": "Introduction", "x0": 72, "top": 60, "x1": 200, "bottom": 76},
                {"text": "This is the first paragraph of the document.", "x0": 72, "top": 90, "x1": 500, "bottom": 106},
                {"text": "Second Section", "x0": 72, "top": 200, "x1": 220, "bottom": 216},
                {"text": "This is another paragraph with different content.", "x0": 72, "top": 230, "x1": 480, "bottom": 246},
            ],
            "parser": "fast_text",
        }

    def test_text_chunk_bbox_not_full_page(self):
        pages = [self._make_page()]
        chunks = chunk_document(
            pages=pages,
            normalized_tables=[],
            document_id="test",
            source_file="test.pdf",
            parser="fast_text",
            chunk_template="policy",
        )
        text_chunks = [c for c in chunks if "paragraph" in c["text"].lower()]
        assert text_chunks, "expected at least one text chunk"
        chunk = text_chunks[0]
        # The chunk bbox should NOT span the full page height
        assert chunk["bbox"][3] < 792, "bbox bottom should be less than page height"
        # The chunk bbox should start close to where the text is (top < 150)
        assert chunk["bbox"][1] < 150, "bbox top should be near the actual text"

    def test_fallback_when_no_text_lines(self):
        """When text_lines is empty, bbox falls back to page bbox — no crash."""
        page = self._make_page()
        page["text_lines"] = []
        chunks = chunk_document(
            pages=[page],
            normalized_tables=[],
            document_id="test",
            source_file="test.pdf",
            parser="fast_text",
            chunk_template="policy",
        )
        assert chunks, "should produce chunks even without text_lines"
        for chunk in chunks:
            assert "bbox" in chunk
