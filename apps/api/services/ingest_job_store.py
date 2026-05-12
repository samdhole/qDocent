# pattern: Imperative Shell
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from apps.api.services import ingest_job_ttl

_DB_PATH: Path = Path("data/ingest_jobs.db")
_LOCK = Lock()
_JOB_TTL = timedelta(minutes=60)


def _ensure_table(conn: sqlite3.Connection) -> None:
    """Create the jobs table if it doesn't exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id     TEXT PRIMARY KEY,
            filename   TEXT,
            status     TEXT,
            created_at TEXT,
            updated_at TEXT,
            result     TEXT,
            error      TEXT
        )
        """
    )
    conn.commit()


def _now_iso() -> str:
    """Return current time as timezone-aware ISO string."""
    return datetime.now(tz=timezone.utc).isoformat()


def create_job(job_id: str, filename: str) -> None:
    """Create a new ingest job with status=queued."""
    now = _now_iso()
    with _LOCK:
        conn = sqlite3.connect(str(_DB_PATH))
        try:
            _ensure_table(conn)
            conn.execute(
                """
                INSERT INTO jobs (job_id, filename, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, filename, "queued", now, now),
            )
            conn.commit()
        finally:
            conn.close()


def update_job(job_id: str, **changes: Any) -> None:
    """
    Update a job with the given changes.
    If 'updated_at' is not in changes, auto-stamp it to current time.
    """
    if "updated_at" not in changes:
        changes["updated_at"] = _now_iso()

    # Build UPDATE statement dynamically
    set_clauses = []
    values = []
    for key, value in changes.items():
        set_clauses.append(f"{key} = ?")
        # Serialize result dict to JSON
        if key == "result" and isinstance(value, dict):
            value = json.dumps(value)
        values.append(value)

    values.append(job_id)

    with _LOCK:
        conn = sqlite3.connect(str(_DB_PATH))
        try:
            _ensure_table(conn)
            query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE job_id = ?"
            conn.execute(query, values)
            conn.commit()
        finally:
            conn.close()


def get_job(job_id: str) -> dict[str, Any] | None:
    """
    Get a job by ID.
    Returns None if job doesn't exist or if it's an expired terminal job (evicted).
    """
    with _LOCK:
        conn = sqlite3.connect(str(_DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            _ensure_table(conn)
            cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            job_dict = dict(row)

            # Check if job is expired (terminal + older than TTL)
            if ingest_job_ttl.is_terminal(job_dict["status"]) and ingest_job_ttl.is_expired(
                job_dict["updated_at"], _JOB_TTL
            ):
                # Evict the job (delete from DB) and return None
                conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
                conn.commit()
                return None

            # Deserialize result JSON if present
            if job_dict["result"] is not None:
                job_dict["result"] = json.loads(job_dict["result"])

            return job_dict

        finally:
            conn.close()


def mark_stale_running_jobs() -> None:
    """
    Flip any jobs with status='running' to status='failed' with error='interrupted by restart'.
    Also refresh updated_at to current time so the job gets a full TTL window.
    """
    now = _now_iso()
    with _LOCK:
        conn = sqlite3.connect(str(_DB_PATH))
        try:
            _ensure_table(conn)
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, error = ?, updated_at = ?
                WHERE status = ?
                """,
                ("failed", "interrupted by restart", now, "running"),
            )
            conn.commit()
        finally:
            conn.close()
