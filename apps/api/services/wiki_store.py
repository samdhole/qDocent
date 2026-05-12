# pattern: Imperative Shell
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_DB_PATH: Path = Path("data/wiki.db")
_LOCK = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS wiki_jobs (
            job_id     TEXT PRIMARY KEY,
            notebook_id TEXT NOT NULL,
            status     TEXT NOT NULL,
            pages_done INTEGER DEFAULT 0,
            pages_total INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            error      TEXT
        );
        CREATE TABLE IF NOT EXISTS wiki_structure (
            notebook_id  TEXT PRIMARY KEY,
            title        TEXT NOT NULL,
            description  TEXT,
            sections_json TEXT NOT NULL,
            generated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS wiki_pages (
            id              TEXT PRIMARY KEY,
            notebook_id     TEXT NOT NULL,
            slug            TEXT NOT NULL,
            title           TEXT NOT NULL,
            description     TEXT,
            content         TEXT,
            importance      TEXT NOT NULL,
            source_doc_ids_json TEXT,
            related_slugs_json  TEXT,
            generated_at    TEXT,
            UNIQUE(notebook_id, slug)
        );
    """)
    conn.commit()


# ── Job CRUD ────────────────────────────────────────────────────────────────

def create_job(notebook_id: str, job_id: str, pages_total: int = 0) -> dict:
    now = _now_iso()
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                "INSERT INTO wiki_jobs (job_id, notebook_id, status, pages_total, created_at, updated_at) "
                "VALUES (?, ?, 'queued', ?, ?, ?)",
                (job_id, notebook_id, pages_total, now, now),
            )
            conn.commit()
        finally:
            conn.close()
    return {"job_id": job_id, "notebook_id": notebook_id, "status": "queued",
            "pages_done": 0, "pages_total": pages_total, "created_at": now, "updated_at": now}


def get_job(job_id: str) -> dict | None:
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            row = conn.execute("SELECT * FROM wiki_jobs WHERE job_id = ?", (job_id,)).fetchone()
        finally:
            conn.close()
    return dict(row) if row else None


def update_job(job_id: str, **kwargs) -> None:
    _ALLOWED = frozenset({"status", "pages_done", "pages_total", "error"})
    updates = {k: v for k, v in kwargs.items() if k in _ALLOWED}
    if not updates:
        return
    updates["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    values = list(updates.values()) + [job_id]
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(f"UPDATE wiki_jobs SET {set_clause} WHERE job_id = ?", values)
            conn.commit()
        finally:
            conn.close()


def increment_pages_done(job_id: str) -> None:
    """Atomically increment pages_done by 1. Used by parallel page workers so two
    threads can't both read pages_done=N and both write pages_done=N+1, losing
    increments. Performs UPDATE ... SET pages_done = pages_done + 1 inside _LOCK.
    """
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                "UPDATE wiki_jobs SET pages_done = pages_done + 1, updated_at = ? "
                "WHERE job_id = ?",
                (_now_iso(), job_id),
            )
            conn.commit()
        finally:
            conn.close()


def mark_stale_jobs(notebook_id: str) -> None:
    """Flip any running jobs for this notebook to failed (called before re-generation)."""
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                "UPDATE wiki_jobs SET status = 'failed', error = 'superseded', updated_at = ? "
                "WHERE notebook_id = ? AND status = 'running'",
                (_now_iso(), notebook_id),
            )
            conn.commit()
        finally:
            conn.close()


# ── Structure + Page CRUD ────────────────────────────────────────────────────

def store_structure(notebook_id: str, title: str, description: str, sections: list[dict]) -> None:
    now = _now_iso()
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                "INSERT OR REPLACE INTO wiki_structure (notebook_id, title, description, sections_json, generated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (notebook_id, title, description, json.dumps(sections), now),
            )
            conn.commit()
        finally:
            conn.close()


def get_structure(notebook_id: str) -> dict | None:
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            row = conn.execute(
                "SELECT * FROM wiki_structure WHERE notebook_id = ?", (notebook_id,)
            ).fetchone()
        finally:
            conn.close()
    if not row:
        return None
    d = dict(row)
    d["sections"] = json.loads(d.pop("sections_json", "[]"))
    return d


def upsert_page(
    notebook_id: str,
    slug: str,
    title: str,
    description: str,
    importance: str,
    source_doc_ids: list[str],
    related_slugs: list[str],
    content: str | None = None,
) -> None:
    now = _now_iso()
    page_id = f"{notebook_id}:{slug}"
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                "INSERT OR REPLACE INTO wiki_pages "
                "(id, notebook_id, slug, title, description, content, importance, "
                " source_doc_ids_json, related_slugs_json, generated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (page_id, notebook_id, slug, title, description, content, importance,
                 json.dumps(source_doc_ids), json.dumps(related_slugs), now if content else None),
            )
            conn.commit()
        finally:
            conn.close()


def update_page_content(notebook_id: str, slug: str, content: str) -> None:
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute(
                "UPDATE wiki_pages SET content = ?, generated_at = ? "
                "WHERE notebook_id = ? AND slug = ?",
                (content, _now_iso(), notebook_id, slug),
            )
            conn.commit()
        finally:
            conn.close()


def get_page(notebook_id: str, slug: str) -> dict | None:
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            row = conn.execute(
                "SELECT * FROM wiki_pages WHERE notebook_id = ? AND slug = ?",
                (notebook_id, slug),
            ).fetchone()
        finally:
            conn.close()
    if not row:
        return None
    d = dict(row)
    d["source_doc_ids"] = json.loads(d.pop("source_doc_ids_json") or "[]")
    d["related_slugs"] = json.loads(d.pop("related_slugs_json") or "[]")
    return d


def list_pages(notebook_id: str) -> list[dict]:
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            rows = conn.execute(
                "SELECT * FROM wiki_pages WHERE notebook_id = ? ORDER BY importance DESC, slug ASC",
                (notebook_id,),
            ).fetchall()
        finally:
            conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["source_doc_ids"] = json.loads(d.pop("source_doc_ids_json") or "[]")
        d["related_slugs"] = json.loads(d.pop("related_slugs_json") or "[]")
        result.append(d)
    return result


def delete_wiki(notebook_id: str) -> None:
    """Clear all wiki data for a notebook (structure + pages). Jobs are left untouched."""
    with _LOCK:
        conn = _connect()
        try:
            _ensure_tables(conn)
            conn.execute("DELETE FROM wiki_pages WHERE notebook_id = ?", (notebook_id,))
            conn.execute("DELETE FROM wiki_structure WHERE notebook_id = ?", (notebook_id,))
            conn.commit()
        finally:
            conn.close()
