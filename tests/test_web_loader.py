"""Tests for web_loader — mocks trafilatura so no network calls in CI."""
import pytest
from unittest.mock import patch
from packages.ingestion.web_loader import load_url

_SAMPLE_TEXT = "## Introduction\n\nThis is the intro.\n\n## Details\n\nThese are the details."


class TestWebLoader:
    def test_returns_list_of_page_dicts(self):
        with patch("packages.ingestion.web_loader.trafilatura.fetch_url", return_value="<html>..."), \
             patch("packages.ingestion.web_loader.trafilatura.extract", return_value=_SAMPLE_TEXT):
            pages = load_url("https://example.com/docs")
        assert isinstance(pages, list)
        assert len(pages) >= 1

    def test_each_page_has_required_fields(self):
        with patch("packages.ingestion.web_loader.trafilatura.fetch_url", return_value="<html>"), \
             patch("packages.ingestion.web_loader.trafilatura.extract", return_value=_SAMPLE_TEXT):
            pages = load_url("https://example.com/docs")
        required = {"page_number", "text", "tables", "confidence", "bbox", "text_lines", "parser"}
        for page in pages:
            assert required <= set(page.keys())

    def test_content_from_text(self):
        with patch("packages.ingestion.web_loader.trafilatura.fetch_url", return_value="<html>"), \
             patch("packages.ingestion.web_loader.trafilatura.extract", return_value=_SAMPLE_TEXT):
            pages = load_url("https://example.com/docs")
        all_text = " ".join(p["text"] for p in pages)
        assert "intro" in all_text.lower()
        assert "details" in all_text.lower()

    def test_parser_field_is_web(self):
        with patch("packages.ingestion.web_loader.trafilatura.fetch_url", return_value="<html>"), \
             patch("packages.ingestion.web_loader.trafilatura.extract", return_value=_SAMPLE_TEXT):
            pages = load_url("https://example.com/docs")
        assert all(p["parser"] == "web" for p in pages)

    def test_text_lines_is_empty(self):
        with patch("packages.ingestion.web_loader.trafilatura.fetch_url", return_value="<html>"), \
             patch("packages.ingestion.web_loader.trafilatura.extract", return_value=_SAMPLE_TEXT):
            pages = load_url("https://example.com/docs")
        for p in pages:
            assert p["text_lines"] == []

    def test_fetch_failure_raises_runtime_error(self):
        # fetch_url returns None on failure
        with patch("packages.ingestion.web_loader.trafilatura.fetch_url", return_value=None):
            with pytest.raises(RuntimeError, match="could not fetch"):
                load_url("https://example.com/docs")

    def test_extract_failure_raises_runtime_error(self):
        # extract returns None when content cannot be extracted (e.g. SPA)
        with patch("packages.ingestion.web_loader.trafilatura.fetch_url", return_value="<html>"), \
             patch("packages.ingestion.web_loader.trafilatura.extract", return_value=None):
            with pytest.raises(RuntimeError, match="extracted empty content"):
                load_url("https://example.com/docs")

    def test_javascript_spa_url_raises_clear_error(self):
        # Verifies AC4.3: SPA pages that produce empty content raise a clear error
        with patch("packages.ingestion.web_loader.trafilatura.fetch_url", return_value="<html><body></body></html>"), \
             patch("packages.ingestion.web_loader.trafilatura.extract", return_value=""):
            with pytest.raises(RuntimeError, match="extracted empty content"):
                load_url("https://spa.example.com/")
