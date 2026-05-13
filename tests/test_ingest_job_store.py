# pattern: Test suite for ingest_job_store imperative shell
import json
from datetime import datetime, timedelta, timezone

from apps.api.services import ingest_job_store


class TestCreateAndGet:
    """Test create_job and get_job."""

    def test_create_job_creates_row_queryable_via_get_job(self):
        """AC3.1: create_job creates a row; get_job reads it back."""
        job_id = "test-job-123"
        filename = "sample.pdf"

        ingest_job_store.create_job(job_id, filename)
        result = ingest_job_store.get_job(job_id)

        assert result is not None
        assert result["job_id"] == job_id
        assert result["filename"] == filename
        assert result["status"] == "queued"
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_get_job_multiple_calls_return_same_data(self):
        """AC3.2: Multiple get_job calls return the same job (SQLite persistence)."""
        job_id = "test-job-456"
        filename = "sample.pdf"

        ingest_job_store.create_job(job_id, filename)
        first_read = ingest_job_store.get_job(job_id)
        second_read = ingest_job_store.get_job(job_id)

        assert first_read == second_read
        assert first_read["job_id"] == job_id

    def test_get_nonexistent_job_returns_none(self):
        """AC3.5: get_job for nonexistent ID returns None."""
        result = ingest_job_store.get_job("nonexistent-job-id")
        assert result is None


class TestUpdateJob:
    """Test update_job behavior."""

    def test_update_job_with_result_dict_serializes_deserializes(self):
        """result dict is stored as JSON and retrieved correctly."""
        job_id = "test-job-result"
        ingest_job_store.create_job(job_id, "sample.pdf")

        result_dict = {"chunks": 42, "tokens": 1024}
        ingest_job_store.update_job(job_id, status="completed", result=result_dict)

        job = ingest_job_store.get_job(job_id)
        assert job is not None
        assert job["result"] == result_dict

    def test_update_job_without_updated_at_auto_stamps(self):
        """update_job without explicit updated_at auto-stamps to current time."""
        job_id = "test-job-autostamp"
        ingest_job_store.create_job(job_id, "sample.pdf")

        before = datetime.now(timezone.utc)
        ingest_job_store.update_job(job_id, status="running")
        after = datetime.now(timezone.utc)

        job = ingest_job_store.get_job(job_id)
        assert job is not None
        updated_at_str = job["updated_at"]
        updated_at = datetime.fromisoformat(updated_at_str)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        # Verify updated_at is within ~2 seconds of current time
        assert before <= updated_at <= after + timedelta(seconds=2)

    def test_update_job_with_explicit_updated_at_none_stores_null(self):
        """update_job with explicit updated_at=None stores SQL NULL (no auto-stamp)."""
        job_id = "test-job-null-timestamp"
        ingest_job_store.create_job(job_id, "sample.pdf")

        ingest_job_store.update_job(job_id, status="completed", updated_at=None)

        job = ingest_job_store.get_job(job_id)
        assert job is not None
        assert job["updated_at"] is None

    def test_update_job_with_explicit_updated_at_uses_provided_value(self):
        """update_job with explicit updated_at uses that value, not current time."""
        job_id = "test-job-explicit-timestamp"
        ingest_job_store.create_job(job_id, "sample.pdf")

        specific_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        ingest_job_store.update_job(job_id, status="running", updated_at=specific_time)

        job = ingest_job_store.get_job(job_id)
        assert job is not None
        assert job["updated_at"] == specific_time


class TestMarkStaleRunningJobs:
    """Test mark_stale_running_jobs behavior."""

    def test_mark_stale_running_jobs_flips_running_to_failed(self):
        """AC3.3: mark_stale_running_jobs flips running status to failed."""
        job_id = "test-job-stale"
        ingest_job_store.create_job(job_id, "sample.pdf")
        ingest_job_store.update_job(job_id, status="running")

        ingest_job_store.mark_stale_running_jobs()

        job = ingest_job_store.get_job(job_id)
        assert job is not None
        assert job["status"] == "failed"
        assert job["error"] == "interrupted by restart"

    def test_mark_stale_running_jobs_updates_timestamp(self):
        """AC3.3 consistency: mark_stale_running_jobs sets fresh updated_at."""
        job_id = "test-job-stale-timestamp"
        ingest_job_store.create_job(job_id, "sample.pdf")
        ingest_job_store.update_job(job_id, status="running")

        before_mark = datetime.now(timezone.utc)
        ingest_job_store.mark_stale_running_jobs()
        after_mark = datetime.now(timezone.utc)

        job = ingest_job_store.get_job(job_id)
        assert job is not None
        updated_at = datetime.fromisoformat(job["updated_at"])
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        # Verify updated_at was refreshed to near current time
        assert before_mark <= updated_at <= after_mark + timedelta(seconds=2)

    def test_marked_failed_job_is_not_immediately_evicted(self):
        """AC3.3 consistency: Fresh updated_at prevents immediate TTL eviction."""
        job_id = "test-job-not-evicted"
        ingest_job_store.create_job(job_id, "sample.pdf")
        ingest_job_store.update_job(job_id, status="running")

        ingest_job_store.mark_stale_running_jobs()

        # First get_job call
        job1 = ingest_job_store.get_job(job_id)
        assert job1 is not None
        assert job1["status"] == "failed"

        # Second get_job call immediately after
        job2 = ingest_job_store.get_job(job_id)
        assert job2 is not None  # Not evicted because updated_at was refreshed
        assert job2["status"] == "failed"


class TestTTLEviction:
    """Test TTL-based eviction of terminal jobs."""

    def test_expired_completed_job_is_pruned(self):
        """AC3.4: Terminal job (completed) older than 60 minutes is evicted."""
        job_id = "test-job-expired-completed"
        ingest_job_store.create_job(job_id, "sample.pdf")

        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        ingest_job_store.update_job(job_id, status="completed", updated_at=two_hours_ago.isoformat())

        result = ingest_job_store.get_job(job_id)
        assert result is None

    def test_expired_failed_job_is_pruned(self):
        """AC3.4: Terminal job (failed) older than 60 minutes is evicted."""
        job_id = "test-job-expired-failed"
        ingest_job_store.create_job(job_id, "sample.pdf")

        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        ingest_job_store.update_job(job_id, status="failed", updated_at=two_hours_ago.isoformat())

        result = ingest_job_store.get_job(job_id)
        assert result is None

    def test_non_terminal_job_is_never_pruned(self):
        """AC3.4: Non-terminal job (running) older than 60 minutes is NOT evicted."""
        job_id = "test-job-old-running"
        ingest_job_store.create_job(job_id, "sample.pdf")

        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        ingest_job_store.update_job(job_id, status="running", updated_at=two_hours_ago.isoformat())

        result = ingest_job_store.get_job(job_id)
        assert result is not None
        assert result["status"] == "running"

    def test_recent_completed_job_is_not_pruned(self):
        """AC3.4: Terminal job (completed) within 60 minutes is NOT evicted."""
        job_id = "test-job-recent-completed"
        ingest_job_store.create_job(job_id, "sample.pdf")

        thirty_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
        ingest_job_store.update_job(job_id, status="completed", updated_at=thirty_minutes_ago.isoformat())

        result = ingest_job_store.get_job(job_id)
        assert result is not None
        assert result["status"] == "completed"

    def test_is_expired_handles_none_updated_at(self):
        """AC3.4: get_job returns the job when updated_at is None."""
        job_id = "test-job-null-updated-at"
        ingest_job_store.create_job(job_id, "sample.pdf")

        ingest_job_store.update_job(job_id, status="completed", updated_at=None)

        result = ingest_job_store.get_job(job_id)
        assert result is not None  # safe fallback — None updated_at is not expired


class TestMarkStaleQueued:
    """Finding 3: mark_stale_running_jobs must also clean up queued jobs."""

    def test_mark_stale_also_kills_queued_jobs(self):
        """Queued job created before crash is flipped to failed on restart."""
        job_id = "test-stale-queued"
        ingest_job_store.create_job(job_id, "queued.pdf")
        # status starts as 'queued' — don't advance to 'running'

        ingest_job_store.mark_stale_running_jobs()

        job = ingest_job_store.get_job(job_id)
        assert job is not None
        assert job["status"] == "failed"
        assert job["error"] == "interrupted by restart"


class TestCorruptResultColumn:
    """Finding 4: corrupt result column must not cause unhandled JSONDecodeError."""

    def test_get_job_with_corrupt_result_returns_job_not_500(self):
        """Truncated JSON in result column returns dict with result=None."""
        job_id = "test-corrupt-result"
        ingest_job_store.create_job(job_id, "broken.pdf")
        # Pass a raw string as result — update_job only json.dumps dicts, not strings
        ingest_job_store.update_job(job_id, status="completed", result="{")

        job = ingest_job_store.get_job(job_id)

        assert job is not None
        assert job["result"] is None
        assert "[result corrupted]" in (job["error"] or "")
