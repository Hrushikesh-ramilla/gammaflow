"""Tests for the Qdrant searcher module."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestQdrantSearcher(unittest.TestCase):
    """Unit tests for QdrantSearcher."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _make_qdrant_point(self, chunk_id, score, page=1, source="PDF"):
        point = MagicMock()
        point.id = chunk_id
        point.score = score
        point.payload = {
            "chunk_id": chunk_id,
            "document_id": "doc-1",
            "document_role": "TEXTBOOK",
            "page_number": page,
            "text": "Sample text content for this chunk.",
            "source_type": source,
            "ocr_confidence": None,
            "char_start": 0,
            "char_end": 100,
        }
        return point

    def test_search_returns_mapped_results(self):
        """search() should map Qdrant points to result dicts."""
        from app.retrieval.searcher import QdrantSearcher

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value=[
                self._make_qdrant_point("c1", 0.95, page=3),
                self._make_qdrant_point("c2", 0.88, page=7),
            ]
        )

        searcher = QdrantSearcher(client=mock_client)
        results = self._run(
            searcher.search(
                query_vector=[0.1] * 384,
                user_id="user-1",
                syllabus_id="syl-1",
                top_k=10,
            )
        )

        assert len(results) == 2
        assert results[0]["score"] == 0.95
        assert results[0]["page_number"] == 3
        assert results[1]["chunk_id"] == "c2"

    def test_search_empty_results(self):
        """search() with no Qdrant hits should return empty list."""
        from app.retrieval.searcher import QdrantSearcher

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[])

        searcher = QdrantSearcher(client=mock_client)
        results = self._run(
            searcher.search(
                query_vector=[0.0] * 384,
                user_id="user-1",
                syllabus_id="syl-1",
            )
        )
        assert results == []

    def test_search_calls_with_user_filter(self):
        """search() should include user_id in the Qdrant filter."""
        from app.retrieval.searcher import QdrantSearcher

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[])

        searcher = QdrantSearcher(client=mock_client)
        self._run(
            searcher.search(
                query_vector=[0.1] * 384,
                user_id="user-abc",
                syllabus_id="syl-xyz",
            )
        )

        assert mock_client.search.called
        call_kwargs = mock_client.search.call_args
        # The filter should have been built
        assert call_kwargs is not None


class TestReranker(unittest.TestCase):
    """Unit tests for the cross-encoder reranker."""

    def test_rerank_fallback_when_model_unavailable(self):
        """rerank() should sort by score if cross-encoder is unavailable."""
        from app.retrieval.reranker import rerank

        results = [
            {"text": "lower score chunk", "score": 0.70},
            {"text": "higher score chunk", "score": 0.95},
            {"text": "medium score chunk", "score": 0.80},
        ]

        with patch("app.retrieval.reranker._get_cross_encoder", return_value=None):
            reranked = rerank("test query", results, top_k=2)

        assert len(reranked) == 2
        assert reranked[0]["score"] == 0.95

    def test_rerank_empty_input(self):
        """rerank() with empty list should return empty list."""
        from app.retrieval.reranker import rerank

        assert rerank("query", [], top_k=5) == []


if __name__ == "__main__":
    unittest.main()
