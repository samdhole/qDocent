"""Shared pytest fixtures for all tests."""
import pytest
from apps.api.services import ingest_job_store, notebook_store


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Redirect ingest_job_store._DB_PATH to a temporary SQLite file for all tests.

    This fixture automatically applies to every test, ensuring database isolation
    and preventing tests from writing to the production data/ingest_jobs.db file.
    Also patches notebook_store._DB_PATH and notebook_store._DOCS_BASE_PATH to
    prevent test isolation issues.
    """
    db_file = tmp_path / "test_jobs.db"
    monkeypatch.setattr(ingest_job_store, "_DB_PATH", db_file)
    monkeypatch.setattr(notebook_store, "_DB_PATH", tmp_path / "test_notebooks.db")
    monkeypatch.setattr(notebook_store, "_DOCS_BASE_PATH", tmp_path / "test_documents")
    yield db_file
