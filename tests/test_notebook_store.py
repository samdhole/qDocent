import json
import pytest
from unittest import mock
from apps.api.services import notebook_store


@pytest.fixture(autouse=True)
def isolated_notebook_db(tmp_path, monkeypatch):
    monkeypatch.setattr(notebook_store, "_DB_PATH", tmp_path / "notebooks.db")
    monkeypatch.setattr(notebook_store, "_DOCS_BASE_PATH", tmp_path / "documents")


@pytest.fixture(autouse=True)
def mock_r2r(monkeypatch):
    """Prevent notebook_store from calling real R2R in any test."""
    with mock.patch("apps.api.services.notebook_store._r2r_client") as m:
        m.create_r2r_collection.return_value = "fake-collection-id"
        m.delete_r2r_collection.return_value = None
        m.add_document_to_r2r_collection.return_value = None
        yield m


class TestNotebookCRUD:
    def test_create_and_get(self):
        nb = notebook_store.create_notebook("My NB", "A description")
        assert nb["id"]
        assert nb["name"] == "My NB"
        assert nb["description"] == "A description"
        assert nb["r2r_collection_id"] == "fake-collection-id"
        fetched = notebook_store.get_notebook(nb["id"])
        assert fetched == nb

    def test_get_nonexistent_returns_none(self):
        assert notebook_store.get_notebook("does-not-exist") is None

    def test_list_returns_all(self):
        notebook_store.create_notebook("NB1")
        notebook_store.create_notebook("NB2")
        notebooks = notebook_store.list_notebooks()
        assert len(notebooks) == 2
        assert {n["name"] for n in notebooks} == {"NB1", "NB2"}

    def test_update_name(self):
        nb = notebook_store.create_notebook("Old Name")
        updated = notebook_store.update_notebook(nb["id"], name="New Name")
        assert updated["name"] == "New Name"
        assert updated["updated_at"] >= nb["updated_at"]

    def test_update_ignores_unknown_columns(self):
        nb = notebook_store.create_notebook("Safe")
        # Should not raise and should not inject unknown column
        result = notebook_store.update_notebook(nb["id"], evil_col="DROP TABLE notebooks;--")
        assert result["name"] == "Safe"

    def test_delete_returns_true_when_existed(self):
        nb = notebook_store.create_notebook("To Delete")
        assert notebook_store.delete_notebook(nb["id"]) is True
        assert notebook_store.get_notebook(nb["id"]) is None

    def test_delete_returns_false_when_not_existed(self):
        assert notebook_store.delete_notebook("ghost-id") is False

    def test_delete_cascades_document_membership(self):
        nb = notebook_store.create_notebook("Parent")
        notebook_store.add_document(nb["id"], "doc-1")
        notebook_store.delete_notebook(nb["id"])
        # create new notebook to ensure DB is still alive; list_documents should be empty
        nb2 = notebook_store.create_notebook("Other")
        assert notebook_store.list_documents(nb["id"]) == []


class TestDocumentMembership:
    def test_add_and_list_documents(self):
        nb = notebook_store.create_notebook("NB")
        notebook_store.add_document(nb["id"], "doc-aaa")
        notebook_store.add_document(nb["id"], "doc-bbb")
        docs = notebook_store.list_documents(nb["id"])
        assert len(docs) == 2
        assert {d["document_id"] for d in docs} == {"doc-aaa", "doc-bbb"}

    def test_add_document_idempotent(self):
        nb = notebook_store.create_notebook("NB")
        notebook_store.add_document(nb["id"], "doc-x")
        notebook_store.add_document(nb["id"], "doc-x")  # duplicate — no error
        assert len(notebook_store.list_documents(nb["id"])) == 1

    def test_remove_document(self):
        nb = notebook_store.create_notebook("NB")
        notebook_store.add_document(nb["id"], "doc-z")
        notebook_store.remove_document(nb["id"], "doc-z")
        assert notebook_store.list_documents(nb["id"]) == []

    def test_list_documents_empty_for_new_notebook(self):
        nb = notebook_store.create_notebook("Empty NB")
        assert notebook_store.list_documents(nb["id"]) == []


class TestMigration:
    def _write_manifest(self, docs_base, doc_id, r2r_ids=None):
        doc_dir = docs_base / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "document_id": doc_id,
            "source_file": f"{doc_id}.pdf",
            "r2r_document_ids": r2r_ids or [],
        }
        (doc_dir / "manifest.json").write_text(json.dumps(manifest))

    def test_migration_creates_default_notebook_with_existing_docs(self, tmp_path, monkeypatch):
        docs_base = tmp_path / "documents"
        monkeypatch.setattr(notebook_store, "_DOCS_BASE_PATH", docs_base)
        self._write_manifest(docs_base, "doc-001", ["r2r-uuid-1"])
        self._write_manifest(docs_base, "doc-002", ["r2r-uuid-2"])

        notebook_store.migrate_default_notebook()

        notebooks = notebook_store.list_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0]["name"] == "Default Notebook"

        docs = notebook_store.list_documents(notebooks[0]["id"])
        assert {d["document_id"] for d in docs} == {"doc-001", "doc-002"}

    def test_migration_idempotent_no_duplicates(self, tmp_path, monkeypatch):
        docs_base = tmp_path / "documents"
        monkeypatch.setattr(notebook_store, "_DOCS_BASE_PATH", docs_base)
        self._write_manifest(docs_base, "doc-aaa")

        notebook_store.migrate_default_notebook()
        notebook_store.migrate_default_notebook()  # second call

        notebooks = notebook_store.list_notebooks()
        assert len(notebooks) == 1  # exactly one Default Notebook

        docs = notebook_store.list_documents(notebooks[0]["id"])
        assert len(docs) == 1  # doc-aaa appears exactly once

    def test_migration_fresh_install_no_documents(self, tmp_path, monkeypatch):
        docs_base = tmp_path / "documents"
        monkeypatch.setattr(notebook_store, "_DOCS_BASE_PATH", docs_base)
        # No documents dir or manifests — should not raise

        notebook_store.migrate_default_notebook()

        notebooks = notebook_store.list_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0]["name"] == "Default Notebook"
        assert notebook_store.list_documents(notebooks[0]["id"]) == []

    def test_migration_creates_r2r_collection(self, mock_r2r):
        notebook_store.migrate_default_notebook()
        mock_r2r.create_r2r_collection.assert_called_once_with("Default Notebook")

    def test_migration_calls_add_document_for_each_r2r_id(self, tmp_path, monkeypatch, mock_r2r):
        docs_base = tmp_path / "documents"
        monkeypatch.setattr(notebook_store, "_DOCS_BASE_PATH", docs_base)
        self._write_manifest(docs_base, "doc-001", ["r2r-uuid-1", "r2r-uuid-2"])

        notebook_store.migrate_default_notebook()

        calls = mock_r2r.add_document_to_r2r_collection.call_args_list
        r2r_ids_added = [c[0][1] for c in calls]  # second positional arg
        assert "r2r-uuid-1" in r2r_ids_added
        assert "r2r-uuid-2" in r2r_ids_added

    def test_migration_idempotent_creates_collection_once(self, mock_r2r):
        notebook_store.migrate_default_notebook()
        notebook_store.migrate_default_notebook()
        # On second call, collection already has a real id — should NOT create again
        assert mock_r2r.create_r2r_collection.call_count == 1

    def test_delete_notebook_deletes_r2r_collection_not_documents(self, mock_r2r):
        nb = notebook_store.create_notebook("To Delete")
        notebook_store.delete_notebook(nb["id"])
        mock_r2r.delete_r2r_collection.assert_called_once_with("fake-collection-id")


class TestDocumentCount:
    def test_list_notebooks_includes_document_count_aggregation(self):
        """Test that list_notebooks() returns document_count via LEFT JOIN aggregation."""
        nb = notebook_store.create_notebook("With Docs")
        notebook_store.add_document(nb["id"], "doc-1")
        notebook_store.add_document(nb["id"], "doc-2")

        notebooks = notebook_store.list_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0]["document_count"] == 2

    def test_list_notebooks_document_count_zero_for_empty_notebook(self):
        """Test that a notebook with no documents returns document_count == 0 (not None)."""
        nb = notebook_store.create_notebook("Empty NB")

        notebooks = notebook_store.list_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0]["document_count"] == 0
        assert notebooks[0]["document_count"] is not None

    def test_list_notebooks_document_count_multiple_notebooks(self):
        """Test document_count is correctly aggregated across multiple notebooks."""
        nb1 = notebook_store.create_notebook("NB 1")
        nb2 = notebook_store.create_notebook("NB 2")
        nb3 = notebook_store.create_notebook("NB 3")

        notebook_store.add_document(nb1["id"], "doc-a")
        notebook_store.add_document(nb1["id"], "doc-b")
        notebook_store.add_document(nb2["id"], "doc-c")
        # nb3 has no documents

        notebooks = notebook_store.list_notebooks()
        assert len(notebooks) == 3

        nb1_row = next(n for n in notebooks if n["id"] == nb1["id"])
        nb2_row = next(n for n in notebooks if n["id"] == nb2["id"])
        nb3_row = next(n for n in notebooks if n["id"] == nb3["id"])

        assert nb1_row["document_count"] == 2
        assert nb2_row["document_count"] == 1
        assert nb3_row["document_count"] == 0
