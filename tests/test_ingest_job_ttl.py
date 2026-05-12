# pattern: Test suite for ingest_job_ttl functional core
import pytest
from datetime import datetime, timedelta, timezone

from apps.api.services import ingest_job_ttl


class TestIsTerminal:
    """Test is_terminal predicate."""

    def test_completed_is_terminal(self):
        """completed status is terminal."""
        assert ingest_job_ttl.is_terminal("completed") is True

    def test_failed_is_terminal(self):
        """failed status is terminal."""
        assert ingest_job_ttl.is_terminal("failed") is True

    def test_running_is_not_terminal(self):
        """running status is not terminal."""
        assert ingest_job_ttl.is_terminal("running") is False

    def test_queued_is_not_terminal(self):
        """queued status is not terminal."""
        assert ingest_job_ttl.is_terminal("queued") is False


class TestIsExpired:
    """Test is_expired predicate."""

    def test_none_timestamp_not_expired(self):
        """None updated_at is not expired (safe fallback)."""
        ttl = timedelta(minutes=60)
        assert ingest_job_ttl.is_expired(None, ttl) is False

    def test_malformed_timestamp_not_expired(self):
        """Malformed timestamp is not expired (safe fallback)."""
        ttl = timedelta(minutes=60)
        assert ingest_job_ttl.is_expired("invalid-date", ttl) is False

    def test_old_timestamp_is_expired(self):
        """Terminal job older than ttl is expired."""
        ttl = timedelta(minutes=60)
        old_time = datetime.now(tz=timezone.utc) - timedelta(minutes=65)
        timestamp = old_time.isoformat()

        assert ingest_job_ttl.is_expired(timestamp, ttl) is True

    def test_recent_timestamp_not_expired(self):
        """Terminal job newer than ttl is not expired."""
        ttl = timedelta(minutes=60)
        recent_time = datetime.now(tz=timezone.utc) - timedelta(minutes=30)
        timestamp = recent_time.isoformat()

        assert ingest_job_ttl.is_expired(timestamp, ttl) is False
