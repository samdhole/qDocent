import pytest
from apps.api.services import conversation_store


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(conversation_store, "_DB_PATH", tmp_path / "conversations.db")


class TestCreateConversation:
    def test_returns_conversation_dict(self):
        result = conversation_store.create_conversation("conv-1", "nb-1", "Hello world")
        assert result["r2r_conv_id"] == "conv-1"
        assert result["notebook_id"] == "nb-1"
        assert result["title"] == "Hello world"
        assert "created_at" in result

    def test_truncates_title_to_60_chars(self):
        long_msg = "A" * 100
        result = conversation_store.create_conversation("conv-2", "nb-1", long_msg)
        assert result["title"] == "A" * 60

    def test_uses_untitled_for_none_message(self):
        result = conversation_store.create_conversation("conv-3", "nb-1", None)
        assert result["title"] == "Untitled"

    def test_accepts_null_notebook_id(self):
        result = conversation_store.create_conversation("conv-4", None, "Hi")
        assert result["notebook_id"] is None

    def test_insert_or_ignore_does_not_overwrite(self):
        conversation_store.create_conversation("conv-5", "nb-1", "First message")
        conversation_store.create_conversation("conv-5", "nb-1", "Second message")
        rows = conversation_store.list_conversations()
        assert len(rows) == 1
        assert rows[0]["title"] == "First message"


class TestListConversations:
    def test_returns_all_conversations_without_filter(self):
        conversation_store.create_conversation("conv-1", "nb-1", "First")
        conversation_store.create_conversation("conv-2", "nb-2", "Second")
        results = conversation_store.list_conversations()
        assert len(results) == 2

    def test_filters_by_notebook_id(self):
        conversation_store.create_conversation("conv-1", "nb-1", "First")
        conversation_store.create_conversation("conv-2", "nb-2", "Second")
        results = conversation_store.list_conversations(notebook_id="nb-1")
        assert len(results) == 1
        assert results[0]["r2r_conv_id"] == "conv-1"

    def test_filter_returns_empty_when_no_match(self):
        conversation_store.create_conversation("conv-1", "nb-1", "First")
        results = conversation_store.list_conversations(notebook_id="nb-other")
        assert results == []

    def test_no_filter_includes_null_notebook_conversations(self):
        conversation_store.create_conversation("conv-old", None, "Pre-Phase-8 conversation")
        results = conversation_store.list_conversations()
        assert any(c["r2r_conv_id"] == "conv-old" for c in results)

    def test_null_notebook_excluded_by_notebook_filter(self):
        conversation_store.create_conversation("conv-old", None, "No notebook")
        conversation_store.create_conversation("conv-nb", "nb-1", "Has notebook")
        results = conversation_store.list_conversations(notebook_id="nb-1")
        r2r_ids = [c["r2r_conv_id"] for c in results]
        assert "conv-old" not in r2r_ids
        assert "conv-nb" in r2r_ids

    def test_sorted_newest_first(self):
        conversation_store.create_conversation("conv-a", "nb-1", "First")
        conversation_store.create_conversation("conv-b", "nb-1", "Second")
        results = conversation_store.list_conversations()
        # SQLite ISO timestamps sort lexicographically; newest inserted last = larger timestamp
        assert results[0]["r2r_conv_id"] == "conv-b"
