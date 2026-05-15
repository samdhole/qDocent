# pattern: Imperative Shell
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH: Path = Path("data/conversations.db")
_LOCK = threading.Lock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(_DB_PATH))


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            r2r_conv_id TEXT PRIMARY KEY,
            notebook_id TEXT,
            title       TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            r2r_conv_id TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
        """
    )
    conn.commit()


def create_conversation(
    r2r_conv_id: str,
    notebook_id: str | None,
    first_message: str | None,
) -> dict:
    """Persist conversation metadata. Title = first 60 chars of first_message."""
    title = (first_message or "Untitled")[:60]
    created_at = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        conn = _connect()
        try:
            _ensure_table(conn)
            conn.execute(
                "INSERT OR IGNORE INTO conversations"
                " (r2r_conv_id, notebook_id, title, created_at)"
                " VALUES (?, ?, ?, ?)",
                (r2r_conv_id, notebook_id, title, created_at),
            )
            conn.commit()
        finally:
            conn.close()
    return {
        "r2r_conv_id": r2r_conv_id,
        "notebook_id": notebook_id,
        "title": title,
        "created_at": created_at,
    }


def add_message(r2r_conv_id: str, role: str, content: str) -> None:
    """Append a message (role: 'user' or 'assistant') to conversation history."""
    created_at = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        conn = _connect()
        try:
            _ensure_table(conn)
            conn.execute(
                "INSERT INTO conversation_messages (r2r_conv_id, role, content, created_at)"
                " VALUES (?, ?, ?, ?)",
                (r2r_conv_id, role, content, created_at),
            )
            conn.commit()
        finally:
            conn.close()


def get_messages(r2r_conv_id: str, limit: int = 10) -> list[dict]:
    """Return the last `limit` messages for a conversation, oldest-first."""
    with _LOCK:
        conn = _connect()
        try:
            _ensure_table(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT role, content FROM conversation_messages"
                " WHERE r2r_conv_id = ?"
                " ORDER BY id DESC LIMIT ?",
                (r2r_conv_id, limit),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            conn.close()


def list_conversations(notebook_id: str | None = None) -> list[dict]:
    """Return conversations sorted newest-first. If notebook_id is given, filter to that notebook only."""
    with _LOCK:
        conn = _connect()
        try:
            _ensure_table(conn)
            conn.row_factory = sqlite3.Row
            if notebook_id is not None:
                cursor = conn.execute(
                    "SELECT * FROM conversations WHERE notebook_id = ?"
                    " ORDER BY created_at DESC",
                    (notebook_id,),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM conversations ORDER BY created_at DESC",
                )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
