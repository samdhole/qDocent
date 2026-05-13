"""Tests for format_router — pure function, no I/O needed."""
import pytest
from packages.ingestion.format_router import detect_source_type, SourceType


class TestDetectSourceType:
    def test_pdf_extension(self):
        assert detect_source_type("report.pdf") == SourceType.PDF

    def test_pdf_uppercase(self):
        assert detect_source_type("REPORT.PDF") == SourceType.PDF

    def test_docx(self):
        assert detect_source_type("proposal.docx") == SourceType.DOCX

    def test_pptx(self):
        assert detect_source_type("slides.pptx") == SourceType.PPTX

    def test_http_url(self):
        assert detect_source_type("http://example.com/page") == SourceType.URL

    def test_https_url(self):
        assert detect_source_type("https://docs.python.org/3/") == SourceType.URL

    def test_unknown_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported source"):
            detect_source_type("archive.zip")

    def test_path_with_directories(self):
        assert detect_source_type("/tmp/uploads/report.docx") == SourceType.DOCX

    def test_doc_old_word(self):
        with pytest.raises(ValueError, match="Unsupported source"):
            detect_source_type("old_file.doc")
