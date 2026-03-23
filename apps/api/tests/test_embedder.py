"""Tests for the embedding module."""

import unittest
from unittest.mock import MagicMock, patch


class TestEmbeddingModel(unittest.TestCase):
    """Unit tests for EmbeddingModel."""

    @patch("app.ingestion.embedder.SentenceTransformer")
    def test_embed_text_returns_list_of_floats(self, mock_st_cls):
        """embed_text should return a plain list of floats."""
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3] * 128)
        mock_st_cls.return_value = mock_model

        from app.ingestion.embedder import EmbeddingModel
        em = EmbeddingModel()
        result = em.embed_text("quicksort algorithm")

        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)
        mock_model.encode.assert_called_once()

    @patch("app.ingestion.embedder.SentenceTransformer")
    def test_embed_batch_returns_parallel_lists(self, mock_st_cls):
        """embed_batch should return one embedding per input text."""
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])
        mock_st_cls.return_value = mock_model

        from app.ingestion.embedder import EmbeddingModel
        em = EmbeddingModel()
        texts = ["first text", "second text"]
        results = em.embed_batch(texts)

        assert len(results) == 2
        assert len(results[0]) == 384

    @patch("app.ingestion.embedder.SentenceTransformer")
    def test_embed_empty_batch_returns_empty(self, mock_st_cls):
        """embed_batch with empty input should return empty list without error."""
        mock_model = MagicMock()
        mock_st_cls.return_value = mock_model

        from app.ingestion.embedder import EmbeddingModel
        em = EmbeddingModel()
        assert em.embed_batch([]) == []

    @patch("app.ingestion.embedder.SentenceTransformer")
    def test_progress_callback_called(self, mock_st_cls):
        """embed_batch should invoke the progress callback."""
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode.side_effect = lambda batch, **kw: np.array([[0.0] * 384] * len(batch))
        mock_st_cls.return_value = mock_model

        from app.ingestion.embedder import EmbeddingModel
        em = EmbeddingModel()

        callback_calls = []
        em.embed_batch(["a", "b", "c"], progress_callback=lambda i, t: callback_calls.append((i, t)))
        assert len(callback_calls) > 0


if __name__ == "__main__":
    unittest.main()
