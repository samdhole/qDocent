# pattern: Imperative Shell
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from apps.api.services.notebook_helpers import generate_notebook_id

_DB_PATH: Path = Path("data/notebooks.db")
_DOCS_BASE_PATH: Path = Path("data/documents")
_LOCK = Lock()
_ALLOWED_UPDATE_COLUMNS: frozenset[str] = frozenset({"name", "description"})


def _now_iso() -> str:
    """Return current time as timezone-aware ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    """Open a connection to the notebooks database.

    Ensures the parent directory exists before opening the connection.
    """
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create the notebooks and notebook_documents tables if they don't exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS notebooks (
            id               TEXT PRIMARY KEY,
            name             TEXT NOT NULL,
            description      TEXT,
            r2r_collection_id TEXT NOT NULL DEFAULT '',
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notebook_documents (
            notebook_id TEXT NOT NULL REFERENCES notebooks(id),
            document_id TEXT NOT NULL,
            added_at    TEXT NOT NULL,
            PRIMARY KEY (notebook_id, document_id)
        );
    """
    )
    conn.commit()


def create_notebook(
    name: str,
    description: str | None = None,
    r2r_collection_id: str = "",
) -> dict:
    """Insert a new notebook row.

    Returns a dict with the created notebook's fields.
    r2r_collection_id defaults to '' and is set by Phase 2.

    Args:
        name: Display name for the notebook.
        description: Optional description.
        r2r_collection_id: R2R collection ID (defaults to '', set by Phase 2).

    Returns:
        Dictionary with id, name, description, r2r_collection_id, created_at, updated_at.
    """
    notebook_id = generate_notebook_id()
    now = _now_iso()
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                """
                INSERT INTO notebooks (id, name, description, r2r_collection_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (notebook_id, name, description, r2r_collection_id, now, now),
            )
            conn.commit()
        finally:
            conn.close()
    return {
        "id": notebook_id,
        "name": name,
        "description": description,
        "r2r_collection_id": r2r_collection_id,
        "created_at": now,
        "updated_at": now,
    }


def get_notebook(notebook_id: str) -> dict | None:
    """Get a notebook by ID.

    Returns None if notebook doesn't exist.

    Args:
        notebook_id: ID of the notebook to retrieve.

    Returns:
        Dictionary with notebook fields, or None if not found.
    """
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            row = conn.execute(
                "SELECT * FROM notebooks WHERE id = ?", (notebook_id,)
            ).fetchone()
        finally:
            conn.close()
    return dict(row) if row else None


def list_notebooks() -> list[dict]:
    """List all notebooks, ordered by creation date.

    Returns:
        List of notebook dictionaries, ordered by created_at ascending.
    """
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            rows = conn.execute(
                "SELECT * FROM notebooks ORDER BY created_at ASC"
            ).fetchall()
        finally:
            conn.close()
    return [dict(r) for r in rows]


def update_notebook(notebook_id: str, **kwargs) -> dict | None:
    """Update allowed fields of a notebook.

    Only 'name' and 'description' can be updated. Silently ignores unknown
    columns (prevents column injection). Auto-stamps updated_at.

    Returns the updated notebook or None if not found.

    Args:
        notebook_id: ID of the notebook to update.
        **kwargs: Fields to update (name, description).

    Returns:
        Updated notebook dictionary, or None if not found.
    """
    updates = {k: v for k, v in kwargs.items() if k in _ALLOWED_UPDATE_COLUMNS}
    if not updates:
        return get_notebook(notebook_id)
    updates["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    values = list(updates.values()) + [notebook_id]
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                f"UPDATE notebooks SET {set_clause} WHERE id = ?",
                values,
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM notebooks WHERE id = ?", (notebook_id,)
            ).fetchone()
        finally:
            conn.close()
    return dict(row) if row else None


def delete_notebook(notebook_id: str) -> bool:
    """Delete a notebook and its document membership records.

    Returns True if the notebook existed and was deleted, False otherwise.

    Args:
        notebook_id: ID of the notebook to delete.

    Returns:
        True if notebook was deleted, False if it didn't exist.
    """
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                "DELETE FROM notebook_documents WHERE notebook_id = ?", (notebook_id,)
            )
            cur = conn.execute(
                "DELETE FROM notebooks WHERE id = ?", (notebook_id,)
            )
            conn.commit()
        finally:
            conn.close()
    return cur.rowcount > 0


def add_document(notebook_id: str, document_id: str) -> None:
    """Add a document to a notebook.

    Idempotent: adding the same document twice is safe (no error).

    Args:
        notebook_id: ID of the notebook.
        document_id: ID of the document to add.
    """
    now = _now_iso()
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                """
                INSERT OR IGNORE INTO notebook_documents (notebook_id, document_id, added_at)
                VALUES (?, ?, ?)
                """,
                (notebook_id, document_id, now),
            )
            conn.commit()
        finally:
            conn.close()


def remove_document(notebook_id: str, document_id: str) -> None:
    """Remove a document from a notebook.

    Args:
        notebook_id: ID of the notebook.
        document_id: ID of the document to remove.
    """
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                "DELETE FROM notebook_documents WHERE notebook_id = ? AND document_id = ?",
                (notebook_id, document_id),
            )
            conn.commit()
        finally:
            conn.close()


def list_documents(notebook_id: str) -> list[dict]:
    """List all documents in a notebook, ordered by addition date.

    Args:
        notebook_id: ID of the notebook.

    Returns:
        List of document membership records, ordered by added_at ascending.
    """
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            rows = conn.execute(
                "SELECT * FROM notebook_documents WHERE notebook_id = ? ORDER BY added_at ASC",
                (notebook_id,),
            ).fetchall()
        finally:
            conn.close()
    return [dict(r) for r in rows]


def migrate_default_notebook() -> None:
    """Idempotent startup hook: assign all pre-existing documents to Default Notebook.

    Creates "Default Notebook" in SQLite if not already present, then walks
    _DOCS_BASE_PATH/*/manifest.json and inserts each document_id into
    notebook_documents (INSERT OR IGNORE guarantees idempotency).

    r2r_collection_id is set to '' here; Phase 2 extends this to create the
    real R2R collection and populate the field.
    """
    existing = list_notebooks()
    if any(n["name"] == "Default Notebook" for n in existing):
        notebook_id = next(n["id"] for n in existing if n["name"] == "Default Notebook")
    else:
        nb = create_notebook(name="Default Notebook", description="Auto-created on upgrade")
        notebook_id = nb["id"]

    manifests = sorted(_DOCS_BASE_PATH.glob("*/manifest.json"))
    for manifest_path in manifests:
        try:
            data = json.loads(manifest_path.read_text())
            doc_id = data.get("document_id")
            if doc_id:
                add_document(notebook_id, doc_id)
        except Exception:
            pass
