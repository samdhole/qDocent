# pattern: Functional Core
from datetime import datetime, timedelta, timezone

_TERMINAL_STATUSES = frozenset({"completed", "failed"})


def is_terminal(status: str) -> bool:
    """Return True if the job status is a terminal state (completed or failed)."""
    return status in _TERMINAL_STATUSES


def is_expired(updated_at: str | None, ttl: timedelta) -> bool:
    """
    Return True if a terminal job's updated_at timestamp is older than ttl.
    Returns False for None or unparseable timestamps (safe default: don't evict).
    """
    if updated_at is None:
        return False
    try:
        dt = datetime.fromisoformat(updated_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(tz=timezone.utc) - dt) > ttl
    except ValueError:
        return False
