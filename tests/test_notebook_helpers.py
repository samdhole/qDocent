"""Tests for notebook_helpers.py (Functional Core)."""
import re

import pytest

from apps.api.services.notebook_helpers import generate_notebook_id, slug_from_name


class TestGenerateNotebookId:
    """Tests for generate_notebook_id()."""

    def test_returns_12_char_hex_string(self):
        """Should return a 12-character hexadecimal string."""
        nid = generate_notebook_id()
        assert len(nid) == 12
        assert all(c in "0123456789abcdef" for c in nid)

    def test_unique_across_calls(self):
        """Should generate unique IDs across calls."""
        ids = {generate_notebook_id() for _ in range(100)}
        assert len(ids) == 100, "All 100 generated IDs should be unique"

    def test_matches_hex_pattern(self):
        """Should match the hex pattern exactly."""
        nid = generate_notebook_id()
        assert re.match(r"^[0-9a-f]{12}$", nid)


class TestSlugFromName:
    """Tests for slug_from_name()."""

    def test_basic_normalization(self):
        """Should lowercase and hyphenate spaces."""
        assert slug_from_name("My Notebook") == "my-notebook"

    def test_removes_special_characters(self):
        """Should remove special characters, keeping only alphanumeric and hyphens."""
        assert slug_from_name("Hello, World!") == "hello-world"

    def test_removes_punctuation(self):
        """Should handle various punctuation marks."""
        assert slug_from_name("Project@2024!") == "project2024"
        assert slug_from_name("Test & Demo") == "test-demo"

    def test_collapses_whitespace(self):
        """Should collapse multiple spaces and tabs into single hyphen."""
        assert slug_from_name("A  B  C") == "a-b-c"

    def test_collapses_hyphens(self):
        """Should collapse multiple hyphens into single hyphen."""
        assert slug_from_name("A---B---C") == "a-b-c"

    def test_collapses_mixed_whitespace_and_hyphens(self):
        """Should collapse both spaces and hyphens together."""
        assert slug_from_name("A  B---C  D") == "a-b-c-d"

    def test_strips_leading_trailing_hyphens(self):
        """Should remove leading/trailing hyphens."""
        assert slug_from_name("-my-notebook-") == "my-notebook"

    def test_strips_whitespace_first(self):
        """Should strip whitespace before processing."""
        assert slug_from_name("  My Notebook  ") == "my-notebook"

    def test_all_special_chars_returns_fallback(self):
        """Should return 'notebook' when input normalizes to empty."""
        assert slug_from_name("!!!") == "notebook"
        assert slug_from_name("@#$%") == "notebook"
        assert slug_from_name("   ") == "notebook"
        assert slug_from_name("") == "notebook"

    def test_fallback_with_trailing_hyphens(self):
        """Should return fallback if only hyphens/spaces remain."""
        assert slug_from_name("---") == "notebook"
        assert slug_from_name("-  -  -") == "notebook"

    def test_unicode_and_accents_removed(self):
        """Should remove non-ASCII characters."""
        assert slug_from_name("Café") == "caf"
        assert slug_from_name("Ñotas") == "otas"

    def test_numbers_preserved(self):
        """Should preserve numeric characters."""
        assert slug_from_name("Project 2024") == "project-2024"
        assert slug_from_name("Test123") == "test123"

    def test_long_slug(self):
        """Should handle long names correctly."""
        long_name = "A Very Long Notebook Name With Many Words"
        expected = "a-very-long-notebook-name-with-many-words"
        assert slug_from_name(long_name) == expected

    def test_single_word(self):
        """Should handle single-word names."""
        assert slug_from_name("Project") == "project"
        assert slug_from_name("DATABASE") == "database"
