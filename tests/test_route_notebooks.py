"""Tests for /notebooks route."""
import io
from unittest import mock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from apps.api.main import app

    return TestClient(app)


@pytest.fixture
def mock_store():
    """Mock the notebook_store at the route import path."""
    with mock.patch("apps.api.routes.notebooks.notebook_store") as m:
        yield m


class TestListNotebooks:
    """Test GET /notebooks endpoint."""

    def test_returns_empty_list(self, client, mock_store):
        """GET /notebooks returns 200 with empty list when no notebooks exist."""
        mock_store.list_notebooks.return_value = []
        resp = client.get("/notebooks")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_notebooks(self, client, mock_store):
        """GET /notebooks returns 200 with list of notebooks."""
        nb = {
            "id": "abc",
            "name": "My NB",
            "description": None,
            "r2r_collection_id": "col-1",
            "created_at": "2026-05-12T00:00:00Z",
            "updated_at": "2026-05-12T00:00:00Z",
        }
        mock_store.list_notebooks.return_value = [nb]
        resp = client.get("/notebooks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "abc"
        assert data[0]["name"] == "My NB"


class TestCreateNotebook:
    """Test POST /notebooks endpoint."""

    def test_returns_201_with_notebook(self, client, mock_store):
        """POST /notebooks returns 201 with created notebook."""
        nb = {
            "id": "new-id",
            "name": "NB",
            "description": None,
            "r2r_collection_id": "col-new",
            "created_at": "2026-05-12T00:00:00Z",
            "updated_at": "2026-05-12T00:00:00Z",
        }
        mock_store.create_notebook.return_value = nb
        resp = client.post("/notebooks", json={"name": "NB"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["r2r_collection_id"] == "col-new"
        mock_store.create_notebook.assert_called_once_with(name="NB", description=None)

    def test_create_with_description(self, client, mock_store):
        """POST /notebooks with description passes it to notebook_store."""
        nb = {
            "id": "new-id",
            "name": "NB",
            "description": "My Description",
            "r2r_collection_id": "col-new",
            "created_at": "2026-05-12T00:00:00Z",
            "updated_at": "2026-05-12T00:00:00Z",
        }
        mock_store.create_notebook.return_value = nb
        resp = client.post("/notebooks", json={"name": "NB", "description": "My Description"})
        assert resp.status_code == 201
        mock_store.create_notebook.assert_called_once_with(name="NB", description="My Description")


class TestGetNotebook:
    """Test GET /notebooks/{notebook_id} endpoint."""

    def test_returns_notebook(self, client, mock_store):
        """GET /notebooks/{id} returns 200 with notebook when it exists."""
        nb = {
            "id": "abc",
            "name": "NB",
            "description": None,
            "r2r_collection_id": "col-1",
            "created_at": "2026-05-12T00:00:00Z",
            "updated_at": "2026-05-12T00:00:00Z",
        }
        mock_store.get_notebook.return_value = nb
        resp = client.get("/notebooks/abc")
        assert resp.status_code == 200
        assert resp.json()["id"] == "abc"

    def test_404_when_not_found(self, client, mock_store):
        """GET /notebooks/{id} returns 404 when notebook doesn't exist."""
        mock_store.get_notebook.return_value = None
        resp = client.get("/notebooks/ghost")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestUpdateNotebook:
    """Test PATCH /notebooks/{notebook_id} endpoint."""

    def test_update_name(self, client, mock_store):
        """PATCH /notebooks/{id} updates notebook name."""
        updated_nb = {
            "id": "abc",
            "name": "Updated Name",
            "description": None,
            "r2r_collection_id": "col-1",
            "created_at": "2026-05-12T00:00:00Z",
            "updated_at": "2026-05-12T00:01:00Z",
        }
        mock_store.update_notebook.return_value = updated_nb
        resp = client.patch("/notebooks/abc", json={"name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"
        mock_store.update_notebook.assert_called_once_with("abc", name="Updated Name")

    def test_update_description(self, client, mock_store):
        """PATCH /notebooks/{id} updates notebook description."""
        updated_nb = {
            "id": "abc",
            "name": "NB",
            "description": "New Desc",
            "r2r_collection_id": "col-1",
            "created_at": "2026-05-12T00:00:00Z",
            "updated_at": "2026-05-12T00:01:00Z",
        }
        mock_store.update_notebook.return_value = updated_nb
        resp = client.patch("/notebooks/abc", json={"description": "New Desc"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "New Desc"

    def test_update_name_and_description(self, client, mock_store):
        """PATCH /notebooks/{id} updates both name and description."""
        updated_nb = {
            "id": "abc",
            "name": "New Name",
            "description": "New Desc",
            "r2r_collection_id": "col-1",
            "created_at": "2026-05-12T00:00:00Z",
            "updated_at": "2026-05-12T00:01:00Z",
        }
        mock_store.update_notebook.return_value = updated_nb
        resp = client.patch(
            "/notebooks/abc",
            json={"name": "New Name", "description": "New Desc"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["description"] == "New Desc"

    def test_404_when_notebook_not_found(self, client, mock_store):
        """PATCH /notebooks/{id} returns 404 when notebook doesn't exist."""
        mock_store.update_notebook.return_value = None
        resp = client.patch("/notebooks/ghost", json={"name": "Updated"})
        assert resp.status_code == 404


class TestDeleteNotebook:
    """Test DELETE /notebooks/{notebook_id} endpoint."""

    def test_204_when_deleted(self, client, mock_store):
        """DELETE /notebooks/{id} returns 204 when notebook is deleted."""
        mock_store.delete_notebook.return_value = True
        resp = client.delete("/notebooks/abc")
        assert resp.status_code == 204

    def test_404_when_not_found(self, client, mock_store):
        """DELETE /notebooks/{id} returns 404 when notebook doesn't exist."""
        mock_store.delete_notebook.return_value = False
        resp = client.delete("/notebooks/ghost")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestListNotebookDocuments:
    """Test GET /notebooks/{notebook_id}/documents endpoint."""

    def test_returns_documents(self, client, mock_store):
        """GET /notebooks/{id}/documents returns 200 with list of documents."""
        mock_store.get_notebook.return_value = {"id": "nb-1"}
        mock_store.list_documents.return_value = [
            {"notebook_id": "nb-1", "document_id": "doc-1", "added_at": "2026-05-12T00:00:00Z"},
        ]
        resp = client.get("/notebooks/nb-1/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["document_id"] == "doc-1"

    def test_returns_empty_list_when_no_documents(self, client, mock_store):
        """GET /notebooks/{id}/documents returns empty list when notebook has no documents."""
        mock_store.get_notebook.return_value = {"id": "nb-1"}
        mock_store.list_documents.return_value = []
        resp = client.get("/notebooks/nb-1/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_404_when_notebook_not_found(self, client, mock_store):
        """GET /notebooks/{id}/documents returns 404 when notebook doesn't exist."""
        mock_store.get_notebook.return_value = None
        resp = client.get("/notebooks/ghost/documents")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestIngestNotebookDocument:
    """Test POST /notebooks/{notebook_id}/documents endpoint."""

    def test_201_with_pdf(self, client, mock_store):
        """POST /notebooks/{id}/documents with PDF returns 201 and records membership."""
        mock_store.get_notebook.return_value = {"id": "nb-1", "r2r_collection_id": "col-abc"}
        mock_store.add_document.return_value = None
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake content")

        with mock.patch("apps.api.routes.notebooks.r2r_client.ingest_file_with_pipeline") as mock_ingest:
            mock_ingest.return_value = {"document_id": "doc-new", "status": "ok"}
            resp = client.post(
                "/notebooks/nb-1/documents",
                files={"file": ("report.pdf", fake_pdf, "application/pdf")},
            )

        assert resp.status_code == 201
        assert resp.json()["document_id"] == "doc-new"
        mock_ingest.assert_called_once()
        call_kwargs = mock_ingest.call_args[1]
        assert call_kwargs.get("collection_id") == "col-abc"
        mock_store.add_document.assert_called_once_with("nb-1", "doc-new")

    def test_422_for_non_pdf(self, client, mock_store):
        """POST /notebooks/{id}/documents with non-PDF returns 422 (Unprocessable Entity)."""
        mock_store.get_notebook.return_value = {"id": "nb-1", "r2r_collection_id": "col-abc"}
        resp = client.post(
            "/notebooks/nb-1/documents",
            files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        assert resp.status_code == 422
        assert "pdf" in resp.json()["detail"].lower()

    def test_404_when_notebook_not_found(self, client, mock_store):
        """POST /notebooks/{id}/documents returns 404 when notebook doesn't exist."""
        mock_store.get_notebook.return_value = None
        resp = client.post(
            "/notebooks/ghost/documents",
            files={"file": ("f.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
