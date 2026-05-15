"""Tests for configuration files structural assertions."""
import re
from pathlib import Path

import pytest


class TestR2RGeminiTomlExample:
    """AC1.1: Verify r2r_gemini.toml.example has correct model versions."""

    @pytest.fixture
    def toml_content(self):
        """Read the r2r_gemini.toml.example file."""
        config_path = Path(__file__).parent.parent / "r2r_gemini.toml.example"
        assert config_path.exists(), f"Config file not found at {config_path}"
        return config_path.read_text()

    def test_fast_llm_is_gemini_2_5_flash(self, toml_content):
        """Assert fast_llm is set to gemini-2.5-flash."""
        # Match the pattern: fast_llm = "gemini/gemini-2.5-flash"
        pattern = r'fast_llm\s*=\s*"gemini/gemini-2\.5-flash"'
        assert re.search(
            pattern, toml_content
        ), "fast_llm must be set to 'gemini/gemini-2.5-flash'"

    def test_quality_llm_is_gemini_2_5_flash(self, toml_content):
        """Assert quality_llm is set to gemini-2.5-flash."""
        # Match the pattern: quality_llm = "gemini/gemini-2.5-flash"
        pattern = r'quality_llm\s*=\s*"gemini/gemini-2\.5-flash"'
        assert re.search(
            pattern, toml_content
        ), "quality_llm must be set to 'gemini/gemini-2.5-flash'"

    def test_does_not_contain_gemini_3_flash_preview(self, toml_content):
        """Assert the string 'gemini-3-flash-preview' does not appear anywhere."""
        assert (
            "gemini-3-flash-preview" not in toml_content
        ), "r2r_gemini.toml.example must not contain 'gemini-3-flash-preview'"
