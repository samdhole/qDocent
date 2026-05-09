# pattern: Functional Core Tests
"""Tests for citation_marker_rewriter Functional Core module."""
import unittest
from uuid import UUID

from apps.api.services.citation_marker_rewriter import rewrite_brackets


def _cit(chunk_id: object, doc: str = "doc.pdf") -> dict:
    """Helper to build a minimal citation dict."""
    return {"chunk_id": chunk_id, "document": doc, "page": 1}


def _ctx(chunk_id: object, text: str = "text") -> dict:
    """Helper to build a minimal retrieved context dict."""
    return {"chunk_id": chunk_id, "text": text, "score": 0.85}


class TestCitationMarkerRewriter(unittest.TestCase):
    """Test citation marker rewriting and reordering."""

    def test_ac2_1_single_known_shortid(self):
        """AC2.1: Single known shortid in answer → [1], citation reordered first."""
        answer = "The answer is [93033bd]."
        citations = [_cit("93033bdf-0000-0000-0000-000000000000")]
        retrieved_contexts = [_ctx("93033bdf-0000-0000-0000-000000000000")]

        rewritten, reordered_cits, reordered_ctxs = rewrite_brackets(
            answer, citations, retrieved_contexts
        )

        self.assertEqual(rewritten, "The answer is [1].")
        self.assertEqual(len(reordered_cits), 1)
        self.assertEqual(
            reordered_cits[0]["chunk_id"], "93033bdf-0000-0000-0000-000000000000"
        )
        self.assertEqual(len(reordered_ctxs), 1)
        self.assertEqual(
            reordered_ctxs[0]["chunk_id"], "93033bdf-0000-0000-0000-000000000000"
        )

    def test_ac2_2_multi_citation_prose_order(self):
        """AC2.2: Multi-citation answer; [N] matches prose order; uncited append at end."""
        answer = "First [aaa1111] and second [bbb2222]."
        # Citations in original order: aaa1111, bbb2222, ccc3333 (uncited)
        citations = [
            _cit("aaa11111-1111-1111-1111-111111111111", "doc1.pdf"),
            _cit("bbb22222-2222-2222-2222-222222222222", "doc2.pdf"),
            _cit("ccc33333-3333-3333-3333-333333333333", "doc3.pdf"),
        ]
        retrieved_contexts = [
            _ctx("aaa11111-1111-1111-1111-111111111111", "text1"),
            _ctx("bbb22222-2222-2222-2222-222222222222", "text2"),
            _ctx("ccc33333-3333-3333-3333-333333333333", "text3"),
        ]

        rewritten, reordered_cits, reordered_ctxs = rewrite_brackets(
            answer, citations, retrieved_contexts
        )

        # Answer: aaa1111 → [1], bbb2222 → [2]
        self.assertEqual(rewritten, "First [1] and second [2].")

        # Citations reordered: aaa first (seen first), bbb (seen second), ccc (uncited)
        self.assertEqual(len(reordered_cits), 3)
        self.assertEqual(
            reordered_cits[0]["chunk_id"], "aaa11111-1111-1111-1111-111111111111"
        )
        self.assertEqual(
            reordered_cits[1]["chunk_id"], "bbb22222-2222-2222-2222-222222222222"
        )
        self.assertEqual(
            reordered_cits[2]["chunk_id"], "ccc33333-3333-3333-3333-333333333333"
        )

        # Retrieved contexts reordered in lockstep
        self.assertEqual(
            reordered_ctxs[0]["chunk_id"], "aaa11111-1111-1111-1111-111111111111"
        )
        self.assertEqual(
            reordered_ctxs[1]["chunk_id"], "bbb22222-2222-2222-2222-222222222222"
        )
        self.assertEqual(
            reordered_ctxs[2]["chunk_id"], "ccc33333-3333-3333-3333-333333333333"
        )

    def test_ac2_3_unknown_shortid_passthrough(self):
        """AC2.3: Unknown shortid not in citations → passes through unchanged."""
        answer = "Unknown citation [deadbef]."
        citations = [_cit("93033bdf-0000-0000-0000-000000000000")]
        retrieved_contexts = [_ctx("93033bdf-0000-0000-0000-000000000000")]

        rewritten, reordered_cits, reordered_ctxs = rewrite_brackets(
            answer, citations, retrieved_contexts
        )

        # Unknown shortid stays unchanged
        self.assertEqual(rewritten, "Unknown citation [deadbef].")
        # Citations unchanged (no prose reference)
        self.assertEqual(len(reordered_cits), 1)
        self.assertEqual(
            reordered_cits[0]["chunk_id"], "93033bdf-0000-0000-0000-000000000000"
        )

    def test_ac2_4_empty_citations_noop(self):
        """AC2.4: Empty citations list → returns inputs unchanged, no exception."""
        answer = "Some text [aaa1111]."
        citations = []
        retrieved_contexts = []

        rewritten, reordered_cits, reordered_ctxs = rewrite_brackets(
            answer, citations, retrieved_contexts
        )

        self.assertEqual(rewritten, answer)
        self.assertEqual(reordered_cits, [])
        self.assertEqual(reordered_ctxs, [])

    def test_edge_adjacent_same_shortid(self):
        """Edge: Same shortid appears twice → both replaced with [1]; citation once."""
        answer = "See [aaa1111] and also [aaa1111] again."
        citations = [_cit("aaa11111-1111-1111-1111-111111111111")]
        retrieved_contexts = [_ctx("aaa11111-1111-1111-1111-111111111111")]

        rewritten, reordered_cits, reordered_ctxs = rewrite_brackets(
            answer, citations, retrieved_contexts
        )

        # Both replaced with [1]
        self.assertEqual(rewritten, "See [1] and also [1] again.")
        # Citation appears only once
        self.assertEqual(len(reordered_cits), 1)
        self.assertEqual(
            reordered_cits[0]["chunk_id"], "aaa11111-1111-1111-1111-111111111111"
        )

    def test_edge_citations_shorter_than_contexts(self):
        """Edge: Filtered citations (2) with full retrieved_contexts (3); align by chunk_id."""
        answer = "First [aaa1111] then [bbb2222]."
        # Filtered citations (2 items after filtering)
        citations = [
            _cit("aaa11111-1111-1111-1111-111111111111"),
            _cit("bbb22222-2222-2222-2222-222222222222"),
        ]
        # Full retrieved_contexts (3 items, one extra)
        retrieved_contexts = [
            _ctx("aaa11111-1111-1111-1111-111111111111", "text_a"),
            _ctx("bbb22222-2222-2222-2222-222222222222", "text_b"),
            _ctx("ccc33333-3333-3333-3333-333333333333", "text_c"),
        ]

        rewritten, reordered_cits, reordered_ctxs = rewrite_brackets(
            answer, citations, retrieved_contexts
        )

        self.assertEqual(rewritten, "First [1] then [2].")
        # Reordered contexts align by chunk_id (not positional)
        self.assertEqual(
            reordered_ctxs[0]["chunk_id"], "aaa11111-1111-1111-1111-111111111111"
        )
        self.assertEqual(
            reordered_ctxs[1]["chunk_id"], "bbb22222-2222-2222-2222-222222222222"
        )

    def test_edge_citation_with_no_chunk_id(self):
        """Edge: Citation dict missing chunk_id key → skipped gracefully, no KeyError."""
        answer = "Text with [aaa1111]."
        # First citation has no chunk_id, second has valid chunk_id
        citations = [
            {"document": "doc1.pdf", "page": 1},  # Missing chunk_id
            _cit("aaa11111-1111-1111-1111-111111111111"),
        ]
        retrieved_contexts = [
            _ctx("aaa11111-1111-1111-1111-111111111111"),
        ]

        rewritten, reordered_cits, reordered_ctxs = rewrite_brackets(
            answer, citations, retrieved_contexts
        )

        # aaa1111 should map to [1] (the second citation)
        self.assertEqual(rewritten, "Text with [1].")
        # Citation without chunk_id should remain (reordered at end or untouched)
        self.assertEqual(len(reordered_cits), 2)

    def test_uuid_chunk_ids_are_supported(self):
        """R2R SDK may return UUID objects instead of string chunk IDs."""
        chunk_id = UUID("aaa11111-1111-1111-1111-111111111111")
        answer = "See [aaa1111]."
        citations = [_cit(chunk_id)]
        retrieved_contexts = [_ctx(chunk_id)]

        rewritten, reordered_cits, reordered_ctxs = rewrite_brackets(
            answer, citations, retrieved_contexts
        )

        self.assertEqual(rewritten, "See [1].")
        self.assertEqual(reordered_cits[0]["chunk_id"], chunk_id)
        self.assertEqual(reordered_ctxs[0]["chunk_id"], chunk_id)


if __name__ == "__main__":
    unittest.main()
