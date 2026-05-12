# pattern: Functional Core
import re
import uuid


def generate_notebook_id() -> str:
    """Generate a unique notebook ID (12-char hex string)."""
    return uuid.uuid4().hex[:12]


def slug_from_name(name: str) -> str:
    """Convert a display name to a URL-safe slug.

    Normalizes whitespace, removes special characters, and returns a
    hyphen-separated lowercase string. Falls back to "notebook" if
    the input normalizes to empty.

    Args:
        name: Display name to slugify.

    Returns:
        URL-safe slug, or "notebook" if input normalizes to empty.
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-") or "notebook"
