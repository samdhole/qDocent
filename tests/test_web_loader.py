"""Tests for web_loader — mocks crawl4ai so no network calls in CI."""
import pytest
from unittest.mock import patch
from packages.ingestion.web_loader import load_url


class FakeCrawlResult:
    success = True
    markdown = "## Introduction\n\nThis is the intro.\n\n## Details\n\nThese are the details."
    error_message = None


class FakeFailResult:
    success = False
    markdown = ""
    error_message = "Network timeout"


class TestWebLoader:
    def test_returns_list_of_page_dicts(self):
        with patch("packages.ingestion.web_loader._fetch_url_markdown", return_value=FakeCrawlResult.markdown):
            pages = load_url("https://example.com/docs")
        assert isinstance(pages, list)
        assert len(pages) >= 1

    def test_each_page_has_required_fields(self):
        with patch("packages.ingestion.web_loader._fetch_url_markdown", return_value=FakeCrawlResult.markdown):
            pages = load_url("https://example.com/docs")
        required = {"page_number", "text", "tables", "confidence", "bbox", "text_lines", "parser"}
        for page in pages:
            assert required <= set(page.keys())

    def test_content_from_markdown(self):
        with patch("packages.ingestion.web_loader._fetch_url_markdown", return_value=FakeCrawlResult.markdown):
            pages = load_url("https://example.com/docs")
        all_text = " ".join(p["text"] for p in pages)
        assert "intro" in all_text.lower()
        assert "details" in all_text.lower()

    def test_parser_field_is_web(self):
        with patch("packages.ingestion.web_loader._fetch_url_markdown", return_value=FakeCrawlResult.markdown):
            pages = load_url("https://example.com/docs")
        assert all(p["parser"] == "web" for p in pages)

    def test_text_lines_is_empty(self):
        with patch("packages.ingestion.web_loader._fetch_url_markdown", return_value=FakeCrawlResult.markdown):
            pages = load_url("https://example.com/docs")
        for p in pages:
            assert p["text_lines"] == []

    def test_fetch_failure_raises_runtime_error(self):
        def fail(_url):
            raise RuntimeError("Network timeout")
        with patch("packages.ingestion.web_loader._fetch_url_markdown", side_effect=fail):
            with pytest.raises(RuntimeError, match="Network timeout"):
                load_url("https://example.com/docs")


class TestSafeBeforeGotoHook:
    """Unit tests for _safe_before_goto SSRF guard hook (Finding 1 — Playwright layer)."""

    def _run(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_blocks_loopback_ip(self):
        from packages.ingestion.web_loader import _safe_before_goto

        loopback = [(None, None, None, None, ("127.0.0.1", 0))]
        with patch("socket.getaddrinfo", return_value=loopback):
            with pytest.raises(RuntimeError, match="SSRF blocked"):
                self._run(_safe_before_goto(None, None, "http://evil.example.com/", None))

    def test_blocks_private_network_ip(self):
        from packages.ingestion.web_loader import _safe_before_goto

        private = [(None, None, None, None, ("192.168.1.100", 0))]
        with patch("socket.getaddrinfo", return_value=private):
            with pytest.raises(RuntimeError, match="SSRF blocked"):
                self._run(_safe_before_goto(None, None, "http://internal.corp/", None))

    def test_allows_public_ip(self):
        from packages.ingestion.web_loader import _safe_before_goto

        public = [(None, None, None, None, ("93.184.216.34", 0))]
        with patch("socket.getaddrinfo", return_value=public):
            # Must not raise
            self._run(_safe_before_goto(None, None, "https://example.com/", None))

    def test_blocks_on_dns_resolution_failure(self):
        from packages.ingestion.web_loader import _safe_before_goto

        with patch("socket.getaddrinfo", side_effect=OSError("NXDOMAIN")):
            with pytest.raises(RuntimeError, match="SSRF blocked"):
                self._run(_safe_before_goto(None, None, "http://unknown.example.com/", None))
