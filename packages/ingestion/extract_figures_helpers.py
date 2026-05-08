# pattern: Functional Core
from __future__ import annotations

import re
from typing import Any

# Matches: "Figure 1:", "Fig. 2 —", "FIGURE 3.", "fig 4 text", etc.
_CAPTION_RE = re.compile(r"^\s*fig(?:ure)?\.?\s*\d+[:.\-\s]", re.I)


def figure_id_from(
    document_id: str,
    page_number: int,
    image_number: int,
    rect_index: int,
) -> str:
    """Return a deterministic figure ID from fixed inputs.

    Determinism is critical: re-ingesting the same PDF must produce
    identical IDs so assets are overwritten, not duplicated.
    """
    return f"{document_id}_p{page_number:03d}_fig{image_number:03d}_{rect_index:02d}"


def nearest_caption(blocks: list[tuple], rect: Any) -> str:
    """Return the closest Figure N caption within 160 px of rect, or ''.

    rect must expose .y0 and .y1 attributes (a fitz.Rect or any duck-typed
    equivalent). Only blocks matching _CAPTION_RE within 160 px vertical
    distance are considered.
    """
    candidates: list[tuple[float, str]] = []
    for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        normalized = " ".join(str(text).split())
        if not _CAPTION_RE.match(normalized):
            continue
        distance = min(abs(y0 - rect.y1), abs(rect.y0 - y1))
        if distance <= 160:
            candidates.append((distance, normalized))
    if not candidates:
        return ""
    return sorted(candidates)[0][1]
