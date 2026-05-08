# pattern: Imperative Shell
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOCUMENTS_DIR = Path("data/documents")


def save_source_pdf(source_path: str | Path, *, document_id: str, source_file: str) -> Path:
    """Copy an uploaded source PDF into stable document storage."""
    target_dir = DOCUMENTS_DIR / _safe_segment(document_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / _safe_pdf_name(source_file)
    shutil.copyfile(source_path, target)
    return target


def write_document_manifest(
    document_id: str,
    *,
    source_file: str,
    r2r_document_ids: list[str],
) -> dict[str, Any]:
    """Persist local metadata needed for later R2R cleanup."""
    target_dir = DOCUMENTS_DIR / _safe_segment(document_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "document_id": _safe_segment(document_id),
        "source_file": _safe_pdf_name(source_file),
        "r2r_document_ids": list(dict.fromkeys(r2r_document_ids)),
    }
    (target_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def load_document_manifest(document_id: str) -> dict[str, Any] | None:
    """Load persisted document metadata, if available."""
    manifest_path = DOCUMENTS_DIR / _safe_segment(document_id) / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def source_pdf_path(document_id: str) -> Path | None:
    """Return the stored source PDF for a document ID, if present."""
    target_dir = DOCUMENTS_DIR / _safe_segment(document_id)
    if not target_dir.exists():
        return None
    matches = sorted(target_dir.glob("*.pdf"))
    return matches[0] if matches else None


def list_source_documents() -> list[dict[str, Any]]:
    """List stored source PDFs newest first."""
    if not DOCUMENTS_DIR.exists():
        return []

    documents: list[dict[str, Any]] = []
    for doc_dir in DOCUMENTS_DIR.iterdir():
        if not doc_dir.is_dir():
            continue
        pdfs = sorted(doc_dir.glob("*.pdf"))
        if not pdfs:
            continue
        pdf = pdfs[0]
        stat = pdf.stat()
        documents.append(
            {
                "document_id": doc_dir.name,
                "source_file": pdf.name,
                "source_url": f"/documents/{doc_dir.name}/source",
                "size_bytes": stat.st_size,
                "updated_at": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )

    return sorted(documents, key=lambda d: d["updated_at"], reverse=True)


def delete_source_document(document_id: str) -> bool:
    """Delete the local stored source PDF directory for a document ID."""
    target_dir = DOCUMENTS_DIR / _safe_segment(document_id)
    if not target_dir.exists() or not target_dir.is_dir():
        return False
    shutil.rmtree(target_dir)
    return True


def _safe_segment(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    if not sanitized:
        raise ValueError(f"document_id {value!r} sanitizes to empty string")
    return sanitized


def _safe_pdf_name(value: str) -> str:
    name = Path(value).name
    stem = _safe_segment(Path(name).stem)
    return f"{stem}.pdf"
