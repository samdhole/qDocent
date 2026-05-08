"""Convert raw camelot table DataFrames to LLM-readable sentence form.

Rule-based (deterministic) for ~90% of tables.
The CONTEXT.md 60/30/10 rule permits LLM calls only for ambiguous multi-header
tables — that path is stubbed here for Phase 3; implement when needed.

Dual storage: raw_table_markdown AND normalized_table_text on every table chunk.
"""
from __future__ import annotations

import re

import pandas as pd


def normalize_table(df: pd.DataFrame, page_number: int, bbox: list[float]) -> dict:
    """Return a table dict with both raw markdown and normalized sentence text.

    Output schema (stored in chunk metadata):
        raw_table_markdown: str
        normalized_table_text: str
        page_number: int
        bbox: list[float]
    """
    df = _clean_dataframe(df)
    raw_md = _to_markdown(df)
    normalized = _to_sentences(df)
    return {
        "raw_table_markdown": raw_md,
        "normalized_table_text": normalized,
        "page_number": page_number,
        "bbox": bbox,
    }


def normalize_page_tables(page_dict: dict) -> list[dict]:
    """Normalize all tables extracted from a single page dict."""
    result = []
    for t in page_dict.get("tables", []):
        df = t.get("df")
        if df is None or df.empty:
            continue
        result.append(
            normalize_table(
                df=df,
                page_number=page_dict["page_number"],
                bbox=t.get("bbox", page_dict.get("bbox", [])),
            )
        )
    return result


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove empty rows/columns, promote first row to header if needed."""
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df = df.fillna("")
    df = df.map(lambda x: re.sub(r"\s+", " ", str(x)).strip())
    # If first row looks like a header (short strings, no numbers), promote it
    first_row = df.iloc[0].tolist()
    if all(len(str(v)) < 40 and not any(c.isdigit() for c in str(v)) for v in first_row):
        df.columns = first_row
        df = df.iloc[1:].reset_index(drop=True)
    return df


def _to_markdown(df: pd.DataFrame) -> str:
    """Convert DataFrame to markdown table string."""
    return df.to_markdown(index=False)


def _to_sentences(df: pd.DataFrame) -> str:
    """Convert DataFrame rows to readable sentences.

    Pattern: "[Context]. The [col1] is [val1], [col2] is [val2], ..."
    Handles up to 8 columns cleanly. Larger tables truncate to top 20 rows.
    """
    cols = list(df.columns)
    if not cols:
        return ""

    # First column is typically the item/subject
    subject_col = cols[0]
    descriptor_cols = cols[1:]

    sentences = []
    for _, row in df.head(20).iterrows():
        subject = str(row[subject_col]).strip()
        if not subject:
            continue
        parts = []
        for col in descriptor_cols:
            val = str(row[col]).strip()
            if val:
                parts.append(f"{col.lower()} {val}")
        if parts:
            sentence = f"The {subject} has {', '.join(parts)}."
        else:
            sentence = f"{subject}."
        sentences.append(sentence)

    if not sentences:
        return ""

    header = f"Table with columns: {', '.join(cols)}."
    return header + " " + " ".join(sentences)
