"""Tests for extract_figures Imperative Shell module."""
import json
from pathlib import Path
from unittest import mock

import fitz
import pytest

import packages.ingestion.extract_figures as extract_figures_mod
from packages.ingestion.extract_figures import extract_figures, write_figure_manifest

_REQUIRED_RECORD_KEYS = {
    "content_type",
    "figure_id",
    "document_id",
    "source_file",
    "page_number",
    "bbox",
    "asset_path",
    "image_url",
    "caption",
    "ocr_text",
}


def _make_pdf_with_image(tmp_path: Path) -> Path:
    """Create a minimal one-page PDF with one embedded raster image."""
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)

    # Create a small 100x100 red pixel block as a PNG in memory
    import struct, zlib

    def _png_bytes(width: int = 100, height: int = 100) -> bytes:
        raw = b"\x00" + b"\xff\x00\x00" * width
        raw_data = raw * height
        compressed = zlib.compress(raw_data)
        def chunk(tag: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            return length + tag + data + crc
        signature = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        return (
            signature
            + chunk(b"IHDR", ihdr_data)
            + chunk(b"IDAT", compressed)
            + chunk(b"IEND", b"")
        )

    png_data = _png_bytes()
    page.insert_image(fitz.Rect(50, 50, 150, 150), stream=png_data)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestExtractFigures:
    """Integration tests for extract_figures()."""

    def test_empty_pdf_returns_empty_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """PDF with no embedded images returns []."""
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", tmp_path / "figures")

        # Create a text-only PDF
        pdf_path = tmp_path / "empty.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Hello world")
        doc.save(str(pdf_path))
        doc.close()

        result = extract_figures(str(pdf_path), "empty_doc", "empty.pdf")
        assert result == []

    def test_record_schema(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Each record contains all required keys."""
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", tmp_path / "figures")
        pdf_path = _make_pdf_with_image(tmp_path)

        result = extract_figures(str(pdf_path), "test_doc", "test.pdf")

        assert len(result) >= 1
        for record in result:
            assert _REQUIRED_RECORD_KEYS.issubset(record.keys()), f"Missing keys: {_REQUIRED_RECORD_KEYS - record.keys()}"

    def test_png_files_created(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """PNG files are saved to disk for each extracted figure."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", figures_dir)
        pdf_path = _make_pdf_with_image(tmp_path)

        result = extract_figures(str(pdf_path), "test_doc", "test.pdf")

        assert len(result) >= 1
        for record in result:
            assert Path(record["asset_path"]).exists(), f"PNG not found: {record['asset_path']}"

    def test_figures_json_written(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """figures.json is written to the document directory with correct source_file."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", figures_dir)
        pdf_path = _make_pdf_with_image(tmp_path)

        extract_figures(str(pdf_path), "test_doc", "test.pdf")

        json_path = figures_dir / "test_doc" / "figures.json"
        assert json_path.exists()
        records = json.loads(json_path.read_text(encoding="utf-8"))
        assert isinstance(records, list)
        assert len(records) >= 1
        # AC6.2: source_file in records is the original filename, not the temp path
        assert records[0]["source_file"] == "test.pdf"

    def test_figure_id_deterministic(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Running extract_figures twice on the same PDF produces identical figure IDs."""
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", tmp_path / "figures")
        pdf_path = _make_pdf_with_image(tmp_path)

        result_a = extract_figures(str(pdf_path), "det_doc", "test.pdf")
        result_b = extract_figures(str(pdf_path), "det_doc", "test.pdf")

        ids_a = [r["figure_id"] for r in result_a]
        ids_b = [r["figure_id"] for r in result_b]
        assert ids_a == ids_b

    def test_small_images_excluded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Images smaller than min_width × min_height are excluded."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", figures_dir)
        pdf_path = _make_pdf_with_image(tmp_path)

        # Require very large minimum — the 100×100 image will be filtered out
        result = extract_figures(str(pdf_path), "test_doc", "test.pdf", min_width=500, min_height=500)
        assert result == []

    def test_source_file_in_records(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """source_file in each record matches the parameter, not the path."""
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", tmp_path / "figures")
        pdf_path = _make_pdf_with_image(tmp_path)

        result = extract_figures(str(pdf_path), "test_doc", "original_upload.pdf")

        for record in result:
            assert record["source_file"] == "original_upload.pdf"

    def test_ocr_failure_returns_empty_string(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """OCR failure is caught silently and returns ocr_text=''."""
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", tmp_path / "figures")
        pdf_path = _make_pdf_with_image(tmp_path)

        with mock.patch(
            "packages.ingestion.extract_figures.pytesseract.image_to_string",
            side_effect=Exception("tesseract not found"),
        ):
            result = extract_figures(str(pdf_path), "test_doc", "test.pdf")

        assert len(result) >= 1
        for record in result:
            assert record["ocr_text"] == ""


class TestWriteFigureManifest:
    """Tests for write_figure_manifest()."""

    def test_returns_none_for_empty_figures(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """No file written and None returned when figures list is empty."""
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", tmp_path / "figures")
        result = write_figure_manifest("empty_doc", [])
        assert result is None
        assert not (tmp_path / "figures" / "empty_doc" / "figures.md").exists()

    def test_writes_markdown_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """figures.md is created when figures are provided."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", figures_dir)

        figures = [{
            "figure_id": "doc_p001_fig001_01",
            "source_file": "report.pdf",
            "page_number": 1,
            "image_url": "/figures/doc/doc_p001_fig001_01.png",
            "caption": "Figure 1: Architecture",
            "ocr_text": "some text",
        }]

        result = write_figure_manifest("doc", figures)

        assert result is not None
        assert result.exists()

    def test_each_figure_has_heading(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Each figure appears as a ## heading with Figure ID on the next line."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(extract_figures_mod, "FIGURES_DIR", figures_dir)

        figures = [
            {
                "figure_id": "doc_p001_fig001_01",
                "source_file": "report.pdf",
                "page_number": 1,
                "image_url": "/figures/doc/doc_p001_fig001_01.png",
                "caption": "Figure 1: Chart",
                "ocr_text": "revenue data",
            },
            {
                "figure_id": "doc_p002_fig001_01",
                "source_file": "report.pdf",
                "page_number": 2,
                "image_url": "/figures/doc/doc_p002_fig001_01.png",
                "caption": "",
                "ocr_text": "",
            },
        ]

        path = write_figure_manifest("doc", figures)
        content = path.read_text(encoding="utf-8")

        assert "## Figure ID: doc_p001_fig001_01" in content
        assert "## Figure ID: doc_p002_fig001_01" in content
        assert "Source file: report.pdf" in content
        assert "Caption: Figure 1: Chart" in content
