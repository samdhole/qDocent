import json
import pytest
from apps.api.services import notebook_store


@pytest.fixture(autouse=True)
def isolated_notebook_db(tmp_path, monkeypatch):
    monkeypatch.setattr(notebook_store, "_DB_PATH", tmp_path / "notebooks.db")
    monkeypatch.setattr(notebook_store, "_DOCS_BASE_PATH", tmp_path / "documents")


class TestNotebookCRUD:
    def test_create_and_get(self):
        nb = notebook_store.create_notebook("My NB", "A description")
        assert nb["id"]
        assert nb["name"] == "My NB"
        assert nb["description"] == "A description"
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
