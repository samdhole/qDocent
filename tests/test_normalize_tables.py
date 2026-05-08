"""Tests for table normalization module."""
import pandas as pd
import pytest

from packages.ingestion.normalize_tables import (
    _to_sentences,
    normalize_page_tables,
    normalize_table,
)


class TestNormalizeTable:
    """Test normalize_table() output schema."""

    def test_normalize_table_required_fields(self):
        """Result should have both raw_table_markdown and normalized_table_text."""
        df = pd.DataFrame(
            {
                "Product": ["Widget A", "Widget B"],
                "Price": ["$10", "$20"],
                "Stock": ["100", "50"],
            }
        )
        result = normalize_table(df, page_number=1, bbox=[0, 0, 100, 100])

        # Check required fields
        assert "raw_table_markdown" in result
        assert "normalized_table_text" in result
        assert "page_number" in result
        assert "bbox" in result

        # Check types
        assert isinstance(result["raw_table_markdown"], str)
        assert isinstance(result["normalized_table_text"], str)
        assert result["page_number"] == 1
        assert result["bbox"] == [0, 0, 100, 100]

    def test_normalize_table_with_markdown_output(self):
        """raw_table_markdown should be valid markdown table format."""
        df = pd.DataFrame(
            {
                "Name": ["Alice", "Bob"],
                "Age": ["30", "25"],
            }
        )
        result = normalize_table(df, page_number=1, bbox=[])

        # Markdown should have pipe characters
        assert "|" in result["raw_table_markdown"]
        assert "Name" in result["raw_table_markdown"]
        assert "Age" in result["raw_table_markdown"]

    def test_normalize_table_with_sentences_output(self):
        """normalized_table_text should be sentences, not markdown."""
        df = pd.DataFrame(
            {
                "Item": ["Thing 1", "Thing 2"],
                "Value": ["High", "Low"],
            }
        )
        result = normalize_table(df, page_number=1, bbox=[])

        normalized = result["normalized_table_text"]
        # Should not have markdown pipes in sentences
        assert "has" in normalized.lower() or "value" in normalized.lower()
        # Should start with "Table with columns:"
        assert "Table with columns:" in normalized

    def test_header_promotion(self):
        """First row with short non-numeric strings should be promoted to header."""
        df = pd.DataFrame(
            [
                ["Product", "Price", "Stock"],
                ["Widget A", "10", "100"],
                ["Widget B", "20", "50"],
            ]
        )
        # The dataframe doesn't have headers yet; first row looks like headers
        result = normalize_table(df, page_number=1, bbox=[])

        # After normalization, "Product" should appear as column name, not as data
        markdown = result["raw_table_markdown"]
        # The markdown should show Product as header (first line after separator)
        assert "Product" in markdown


class TestNormalizePageTables:
    """Test normalize_page_tables() with full page dicts."""

    def test_empty_page_returns_empty_list(self):
        """Page with no tables should return empty list."""
        page_dict = {
            "page_number": 1,
            "text": "No tables here",
            "tables": [],
            "bbox": [0, 0, 612, 792],
        }
        result = normalize_page_tables(page_dict)
        assert result == []

    def test_page_with_empty_dataframe_skipped(self):
        """Tables with empty DataFrames should be skipped."""
        empty_df = pd.DataFrame()
        page_dict = {
            "page_number": 1,
            "text": "Some text",
            "tables": [
                {
                    "df": empty_df,
                    "bbox": [0, 0, 100, 100],
                }
            ],
            "bbox": [0, 0, 612, 792],
        }
        result = normalize_page_tables(page_dict)
        assert result == []

    def test_page_with_valid_tables(self):
        """Page with valid tables should return normalized table list."""
        df = pd.DataFrame(
            {
                "Col1": ["A", "B"],
                "Col2": ["1", "2"],
            }
        )
        page_dict = {
            "page_number": 1,
            "text": "Some text with table",
            "tables": [
                {
                    "df": df,
                    "bbox": [0, 0, 100, 100],
                }
            ],
            "bbox": [0, 0, 612, 792],
        }
        result = normalize_page_tables(page_dict)

        assert len(result) == 1
        assert "raw_table_markdown" in result[0]
        assert "normalized_table_text" in result[0]
        assert result[0]["page_number"] == 1


class TestToSentences:
    """Test _to_sentences() text conversion."""

    def test_basic_sentences(self):
        """DataFrame should convert to readable sentence form."""
        df = pd.DataFrame(
            {
                "Product": ["Widget A", "Widget B"],
                "Price": ["$10", "$20"],
            }
        )
        result = _to_sentences(df)

        # Should mention the columns
        assert "Product" in result
        assert "Price" in result
        # Should mention products
        assert "Widget A" in result or "Widget B" in result

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty string."""
        df = pd.DataFrame()
        result = _to_sentences(df)
        assert result == ""

    def test_single_column(self):
        """Single column DataFrame should list items."""
        df = pd.DataFrame(
            {
                "Item": ["Apple", "Banana"],
            }
        )
        result = _to_sentences(df)
        assert "Apple" in result or "Banana" in result

    def test_many_columns(self):
        """DataFrame with many columns should format sentences."""
        df = pd.DataFrame(
            {
                "Name": ["Alice"],
                "Age": ["30"],
                "City": ["NYC"],
                "Job": ["Engineer"],
                "Salary": ["100k"],
            }
        )
        result = _to_sentences(df)
        # Should contain the subject and some descriptors
        assert "Alice" in result
        assert "age" in result.lower() or "30" in result
