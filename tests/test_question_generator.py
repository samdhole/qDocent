"""Tests for suggested question generation."""
from unittest import mock


class TestBuildPrompt:
    def test_includes_text_previews(self):
        from apps.api.services.question_generator import _build_prompt

        prompt = _build_prompt(["Chunk A content.", "Chunk B content."])

        assert "Chunk A content." in prompt
        assert "Chunk B content." in prompt

    def test_wraps_excerpts_in_delimiters(self):
        """Finding 7: excerpts are wrapped in explicit DATA-only delimiters."""
        from apps.api.services.question_generator import _build_prompt

        prompt = _build_prompt(["Some excerpt."])

        assert "=== BEGIN DOCUMENT EXCERPTS ===" in prompt
        assert "=== END DOCUMENT EXCERPTS ===" in prompt

    def test_delimiter_precedes_excerpt_content(self):
        """BEGIN delimiter appears before the excerpt text."""
        from apps.api.services.question_generator import _build_prompt

        prompt = _build_prompt(["Injected content."])

        begin_pos = prompt.index("=== BEGIN DOCUMENT EXCERPTS ===")
        content_pos = prompt.index("Injected content.")
        assert begin_pos < content_pos

    def test_data_only_instruction_present(self):
        """Prompt instructs model to treat content as DATA ONLY."""
        from apps.api.services.question_generator import _build_prompt

        prompt = _build_prompt(["anything"])

        assert "DATA ONLY" in prompt

    def test_caps_at_max_previews(self):
        from apps.api.services.question_generator import _MAX_PREVIEWS, _build_prompt

        many = [f"Chunk {i}" for i in range(_MAX_PREVIEWS + 5)]
        prompt = _build_prompt(many)

        assert f"Chunk {_MAX_PREVIEWS}" not in prompt

    def test_empty_previews_returns_prompt(self):
        from apps.api.services.question_generator import _build_prompt

        prompt = _build_prompt([])

        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestParseQuestions:
    def test_parses_question_lines(self):
        from apps.api.services.question_generator import _parse_questions

        raw = "What is the refund policy?\nHow long does shipping take?\n"

        assert _parse_questions(raw) == [
            "What is the refund policy?",
            "How long does shipping take?",
        ]

    def test_filters_non_question_lines(self):
        from apps.api.services.question_generator import _parse_questions

        raw = "Here are your questions:\nWhat is the policy?\nThank you."

        assert _parse_questions(raw) == ["What is the policy?"]

    def test_strips_blank_lines(self):
        from apps.api.services.question_generator import _parse_questions

        raw = "\nWhat is X?\n\nWhat is Y?\n"

        assert _parse_questions(raw) == ["What is X?", "What is Y?"]

    def test_empty_string_returns_empty_list(self):
        from apps.api.services.question_generator import _parse_questions

        assert _parse_questions("") == []


class TestGenerateQuestions:
    @mock.patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"})
    @mock.patch("apps.api.services.question_generator.ChatGoogleGenerativeAI")
    def test_returns_parsed_questions(self, mock_llm_class):
        mock_llm = mock.MagicMock()
        mock_llm.invoke.return_value.content = "What is the policy?\nWhat is the deadline?"
        mock_llm_class.return_value = mock_llm

        from apps.api.services.question_generator import generate_questions

        result = generate_questions(["Some document content."])

        assert result == ["What is the policy?", "What is the deadline?"]

    def test_returns_empty_list_when_no_api_key(self):
        import os

        env = {k: v for k, v in os.environ.items() if k != "GOOGLE_API_KEY"}
        with mock.patch.dict("os.environ", env, clear=True):
            from apps.api.services.question_generator import generate_questions

            result = generate_questions(["Some content."])

        assert result == []

    def test_returns_empty_list_on_empty_previews(self):
        from apps.api.services.question_generator import generate_questions

        assert generate_questions([]) == []

    @mock.patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"})
    @mock.patch("apps.api.services.question_generator.ChatGoogleGenerativeAI")
    def test_returns_empty_list_on_llm_error(self, mock_llm_class):
        mock_llm_class.return_value.invoke.side_effect = RuntimeError("LLM unavailable")

        from apps.api.services.question_generator import generate_questions

        result = generate_questions(["Some content."])

        assert result == []
