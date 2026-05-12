import pytest
from unittest import mock
from fastapi.testclient import TestClient
from apps.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_wiki_services():
    """Mock all wiki services at the route import path."""
    with mock.patch("apps.api.routes.wiki.notebook_store") as mock_nb, \
         mock.patch("apps.api.routes.wiki.wiki_store") as mock_ws, \
         mock.patch("apps.api.routes.wiki.wiki_generator") as mock_gen:
        yield mock_nb, mock_ws, mock_gen


class TestGenerateWiki:
    def test_returns_202_with_job_id(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_nb.get_notebook.return_value = {"id": "nb-1", "r2r_collection_id": "col-abc"}
        mock_nb.list_documents.return_value = [{"document_id": "doc-1"}]
        mock_ws.create_job.return_value = {"job_id": "job-abc", "status": "queued"}
        mock_ws.mark_stale_jobs.return_value = None
        mock_gen.generate_wiki.return_value = None

        resp = client.post("/notebooks/nb-1/wiki/generate")

        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "queued"

    def test_422_when_no_documents(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_nb.get_notebook.return_value = {"id": "nb-1", "r2r_collection_id": "col-abc"}
        mock_nb.list_documents.return_value = []

        resp = client.post("/notebooks/nb-1/wiki/generate")

        assert resp.status_code == 422
        assert "no documents" in resp.json()["detail"].lower()

    def test_404_when_notebook_not_found(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_nb.get_notebook.return_value = None

        resp = client.post("/notebooks/ghost/wiki/generate")

        assert resp.status_code == 404


class TestGetWikiJob:
    def test_returns_job(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        job = {"job_id": "job-abc", "notebook_id": "nb-1",
               "status": "running", "pages_done": 2, "pages_total": 5}
        mock_ws.get_job.return_value = job

        resp = client.get("/notebooks/nb-1/wiki/jobs/job-abc")

        assert resp.status_code == 200
        assert resp.json()["pages_done"] == 2

    def test_404_when_job_not_found(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_ws.get_job.return_value = None

        resp = client.get("/notebooks/nb-1/wiki/jobs/ghost")

        assert resp.status_code == 404

    def test_404_when_job_belongs_to_different_notebook(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_ws.get_job.return_value = {"job_id": "job-abc", "notebook_id": "nb-DIFFERENT"}

        resp = client.get("/notebooks/nb-1/wiki/jobs/job-abc")

        assert resp.status_code == 404


class TestGetWiki:
    def test_returns_structure_and_pages(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_ws.get_structure.return_value = {"title": "My Wiki", "sections": []}
        mock_ws.list_pages.return_value = [{"slug": "overview", "title": "Overview"}]

        resp = client.get("/notebooks/nb-1/wiki")

        assert resp.status_code == 200
        data = resp.json()
        assert data["structure"]["title"] == "My Wiki"
        assert len(data["pages"]) == 1

    def test_returns_empty_when_no_wiki(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_ws.get_structure.return_value = None
        mock_ws.list_pages.return_value = []

        resp = client.get("/notebooks/nb-1/wiki")

        assert resp.status_code == 200
        assert resp.json()["structure"] is None
        assert resp.json()["pages"] == []


class TestGetWikiPage:
    def test_returns_page(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        page = {"slug": "overview", "title": "Overview",
                "content": "# Overview\n\nContent.", "source_doc_ids": ["doc-1"]}
        mock_ws.get_page.return_value = page

        resp = client.get("/notebooks/nb-1/wiki/overview")

        assert resp.status_code == 200
        assert resp.json()["content"].startswith("# Overview")

    def test_404_when_slug_not_found(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_ws.get_page.return_value = None

        resp = client.get("/notebooks/nb-1/wiki/ghost-slug")

        assert resp.status_code == 404


class TestDeleteWiki:
    def test_204_on_delete(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_ws.delete_wiki.return_value = None

        resp = client.delete("/notebooks/nb-1/wiki")

        assert resp.status_code == 204
        mock_ws.delete_wiki.assert_called_once_with("nb-1")

    def test_subsequent_get_returns_empty(self, client, mock_wiki_services):
        mock_nb, mock_ws, mock_gen = mock_wiki_services
        mock_ws.delete_wiki.return_value = None
        mock_ws.get_structure.return_value = None
        mock_ws.list_pages.return_value = []

        client.delete("/notebooks/nb-1/wiki")
        resp = client.get("/notebooks/nb-1/wiki")

        assert resp.status_code == 200
        assert resp.json()["structure"] is None
