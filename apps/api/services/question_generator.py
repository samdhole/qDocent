# pattern: Imperative Shell
"""Generate suggested questions from document chunk text previews via Gemini."""
from __future__ import annotations

import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI

log = logging.getLogger(__name__)

_DEFAULT_MODEL = os.getenv("QUESTION_GEN_MODEL", "gemini-3-flash-preview")
_MAX_PREVIEWS = 15


def _build_prompt(text_previews: list[str]) -> str:
    """Build the question-generation prompt from chunk text previews."""
    context = "\n\n---\n\n".join(text_previews[:_MAX_PREVIEWS])
    return (
        "You are a research assistant. Based on the following document excerpts, "
        "generate exactly 6 diverse questions a user might ask about this document. "
        "Return ONLY the questions, one per line, no numbering, no preamble.\n\n"
        f"Document excerpts:\n{context}"
    )


def _parse_questions(raw: str) -> list[str]:
    """Parse LLM output into a clean list of question strings."""
    lines = [line.strip() for line in raw.strip().splitlines()]
    return [line for line in lines if line and line.endswith("?")]


def generate_questions(text_previews: list[str]) -> list[str]:
    """Call Gemini to generate questions from text previews."""
    if not text_previews:
        return []

    if not os.getenv("GOOGLE_API_KEY"):
        log.warning("GOOGLE_API_KEY not set; skipping LLM question generation")
        return []

    try:
        llm = ChatGoogleGenerativeAI(model=_DEFAULT_MODEL, temperature=0.3)
        response = llm.invoke(_build_prompt(text_previews))
        raw: str = getattr(response, "content", "") or str(response)
        return _parse_questions(raw)[:6]
    except Exception as exc:
        log.warning("Question generation failed: %s", exc)
        return []
