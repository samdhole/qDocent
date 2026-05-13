import pytest
from apps.api.services import wiki_store


@pytest.fixture(autouse=True)
def isolated_wiki_db(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_store, "_DB_PATH", tmp_path / "wiki.db")


class TestJobCRUD:
    def test_create_and_get_job(self):
        wiki_store.create_job("nb-1", "job-abc", pages_total=5)
        job = wiki_store.get_job("job-abc")
        assert job["status"] == "queued"
        assert job["pages_total"] == 5

    def test_update_job_status(self):
        wiki_store.create_job("nb-1", "job-x")
        wiki_store.update_job("job-x", status="running", pages_done=2)
        job = wiki_store.get_job("job-x")
        assert job["status"] == "running"
        assert job["pages_done"] == 2

    def test_increment_pages_done_is_atomic(self):
        """Verify parallel increments don't lose updates (no read-modify-write race).
        Uses ThreadPoolExecutor to simulate the production scenario where multiple
        page workers call increment_pages_done concurrently."""
        from concurrent.futures import ThreadPoolExecutor
        wiki_store.create_job("nb-1", "job-inc", pages_total=20)
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda _: wiki_store.increment_pages_done("job-inc"), range(20)))
        job = wiki_store.get_job("job-inc")
        assert job["pages_done"] == 20

    def test_get_nonexistent_returns_none(self):
        assert wiki_store.get_job("ghost") is None


class TestStructureAndPages:
    def test_store_and_get_structure(self):
        sections = [{"id": "s1", "title": "Core", "page_slugs": ["p1"]}]
        wiki_store.store_structure("nb-1", "My Wiki", "Desc", sections)
        struct = wiki_store.get_structure("nb-1")
        assert struct["title"] == "My Wiki"
        assert struct["sections"][0]["id"] == "s1"

    def test_upsert_page_and_get(self):
        wiki_store.upsert_page("nb-1", "overview", "Overview", "Big picture", "high",
                               ["doc-1"], ["arch"])
        page = wiki_store.get_page("nb-1", "overview")
        assert page["title"] == "Overview"
        assert page["source_doc_ids"] == ["doc-1"]
        assert page["content"] is None

    def test_update_page_content(self):
        wiki_store.upsert_page("nb-1", "arch", "Architecture", "", "medium", [], [])
        wiki_store.update_page_content("nb-1", "arch", "# Architecture\n\nContent here.")
        page = wiki_store.get_page("nb-1", "arch")
        assert "Content here" in page["content"]

    def test_upsert_page_idempotent_replace(self):
        wiki_store.upsert_page("nb-1", "slug-1", "Title v1", "", "low", [], [])
        wiki_store.upsert_page("nb-1", "slug-1", "Title v2", "", "high", ["doc-2"], [])
        page = wiki_store.get_page("nb-1", "slug-1")
        assert page["title"] == "Title v2"  # replaced

    def test_list_pages(self):
        wiki_store.upsert_page("nb-1", "p1", "Page1", "", "high", [], [])
        wiki_store.upsert_page("nb-1", "p2", "Page2", "", "low", [], [])
        pages = wiki_store.list_pages("nb-1")
        assert len(pages) == 2

    def test_get_page_not_found(self):
        assert wiki_store.get_page("nb-1", "ghost") is None


class TestDeleteWiki:
    def test_delete_clears_structure_and_pages(self):
        wiki_store.store_structure("nb-1", "T", "D", [])
        wiki_store.upsert_page("nb-1", "p1", "P1", "", "high", [], [])

        wiki_store.delete_wiki("nb-1")

        assert wiki_store.get_structure("nb-1") is None
        assert wiki_store.list_pages("nb-1") == []

    def test_delete_does_not_affect_other_notebooks(self):
        wiki_store.store_structure("nb-1", "T", "D", [])
        wiki_store.store_structure("nb-2", "T2", "D2", [])
        wiki_store.delete_wiki("nb-1")
        assert wiki_store.get_structure("nb-2") is not None


class TestMarkStaleJobs:
    """Finding 3: mark_stale_jobs must clean up both running and queued jobs."""

    def test_mark_stale_jobs_kills_running(self):
        wiki_store.create_job("nb-ms", "job-run")
        wiki_store.update_job("job-run", status="running")

        wiki_store.mark_stale_jobs("nb-ms")

        job = wiki_store.get_job("job-run")
        assert job["status"] == "failed"
        assert job["error"] == "superseded"

    def test_mark_stale_jobs_also_kills_queued(self):
        """Queued wiki job is also marked failed on re-generation (Finding 3)."""
        wiki_store.create_job("nb-ms2", "job-q")
        # status starts as 'queued' — no status update needed

        wiki_store.mark_stale_jobs("nb-ms2")

        job = wiki_store.get_job("job-q")
        assert job["status"] == "failed"
        assert job["error"] == "superseded"
