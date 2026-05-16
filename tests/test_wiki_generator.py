import json
import pytest
from unittest import mock
from apps.api.services import wiki_generator, wiki_store, notebook_store
from apps.api.services.wiki_xml_parser import WikiPageSpec

VALID_XML = """<wiki_structure>
  <title>Test Wiki</title><description>Desc</description>
  <pages>
    <page id="page-1"><title>Overview</title><description>Big picture</description>
      <importance>high</importance><relevant_files/><related_pages/>
    </page>
    <page id="page-2"><title>Details</title><description>In depth</description>
      <importance>medium</importance><relevant_files/><related_pages/>
    </page>
  </pages>
</wiki_structure>"""


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_store, "_DB_PATH", tmp_path / "wiki.db")
    monkeypatch.setattr(notebook_store, "_DB_PATH", tmp_path / "notebooks.db")
    monkeypatch.setattr("apps.api.services.document_store.DOCUMENTS_DIR", tmp_path / "documents")
    # Mock R2R calls on notebook_store (create_notebook calls R2R)
    with mock.patch("apps.api.services.notebook_store._r2r_client") as m:
        m.create_r2r_collection.return_value = "fake-col"
        m.delete_r2r_collection.return_value = None
        yield


@pytest.fixture
def fake_notebook(tmp_path):
    nb = notebook_store.create_notebook("Test NB")
    notebook_store.add_document(nb["id"], "doc-001")
    # Create a minimal manifest
    doc_dir = tmp_path / "documents" / "doc-001"
    doc_dir.mkdir(parents=True)
    (doc_dir / "manifest.json").write_text(json.dumps({
        "document_id": "doc-001", "source_file": "test.pdf", "r2r_document_ids": []
    }))
    return nb


def _mock_llm_response(text: str):
    m = mock.MagicMock()
    m.content = text
    return m


class TestGenerateWiki:
    def test_generates_structure_and_pages(self, fake_notebook):
        nb_id = fake_notebook["id"]
        job = wiki_store.create_job(nb_id, "job-001")

        with mock.patch("apps.api.services.wiki_generator._make_llm") as mock_llm_factory, \
             mock.patch("apps.api.services.wiki_generator.r2r_client.rag_query") as mock_rag:

            mock_rag.return_value = {"retrieved_contexts": [{"text": "chunk text"}]}
            instance = mock_llm_factory.return_value
            # First call → structure XML; subsequent calls → page content
            instance.invoke.side_effect = [
                _mock_llm_response(VALID_XML),
                _mock_llm_response("# Overview\n\nPage content."),
                _mock_llm_response("# Details\n\nMore content."),
            ]

            wiki_generator.generate_wiki(nb_id, "col-abc", "job-001")

        job = wiki_store.get_job("job-001")
        assert job["status"] == "completed"
        assert job["pages_total"] == 2
        assert job["pages_done"] == 2

        structure = wiki_store.get_structure(nb_id)
        assert structure["title"] == "Test Wiki"

        pages = wiki_store.list_pages(nb_id)
        assert len(pages) == 2

    def test_fails_gracefully_when_no_documents(self, tmp_path, monkeypatch):
        with mock.patch("apps.api.services.notebook_store._r2r_client") as m:
            m.create_r2r_collection.return_value = "fake-col"
            nb = notebook_store.create_notebook("Empty NB")
        wiki_store.create_job(nb["id"], "job-empty")
        wiki_generator.generate_wiki(nb["id"], "col-abc", "job-empty")
        job = wiki_store.get_job("job-empty")
        assert job["status"] == "failed"
        assert "No documents" in (job["error"] or "")

    def test_generate_page_content_forwards_all_pages_and_notebook_id(self, fake_notebook):
        """AC2.1: Verify _generate_page_content forwards all_pages + notebook_id kwargs to build_page_prompt."""
        nb_id = fake_notebook["id"]
        pages = [
            WikiPageSpec(
                slug="overview", title="Overview", description="Big picture",
                importance="high", source_doc_ids=[], related_slugs=[]
            ),
            WikiPageSpec(
                slug="details", title="Details", description="In depth",
                importance="medium", source_doc_ids=[], related_slugs=[]
            ),
        ]

        with mock.patch("apps.api.services.wiki_generator.r2r_client.rag_query") as mock_rag, \
             mock.patch("apps.api.services.wiki_generator.build_page_prompt") as mock_prompt, \
             mock.patch("apps.api.services.wiki_generator._make_llm") as mock_llm_factory, \
             mock.patch("apps.api.services.wiki_generator.wiki_store.update_page_content") as mock_update, \
             mock.patch("apps.api.services.wiki_generator.wiki_store.increment_pages_done") as mock_increment:

            mock_rag.return_value = {"retrieved_contexts": [{"text": "chunk text"}]}
            mock_prompt.return_value = "Generated prompt"
            instance = mock_llm_factory.return_value
            instance.invoke.return_value = _mock_llm_response("# Overview\n\nContent.")

            # Call _generate_page_content for the first page
            wiki_generator._generate_page_content(pages[0], nb_id, "col-abc", "job-001", pages)

            # Assert build_page_prompt was called with all_pages and notebook_id kwargs
            mock_prompt.assert_called_once()
            call_args = mock_prompt.call_args
            assert call_args.kwargs.get("all_pages") == pages, "all_pages kwarg not forwarded"
            assert call_args.kwargs.get("notebook_id") == nb_id, "notebook_id kwarg not forwarded"
