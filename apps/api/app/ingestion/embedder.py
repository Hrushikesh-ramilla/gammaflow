"""sentence-transformers embedding module with batch processing."""

import asyncio
from typing import Callable, List, Optional

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.ingestion.chunker import TextChunk

log = structlog.get_logger()


class EmbeddingModule:
    """Generates embeddings for text chunks using sentence-transformers.

    Uses all-MiniLM-L6-v2 (384 dimensions) for cost efficiency.
    Upgradeable to text-embedding-3-small for higher accuracy.
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            log.info("embedder.loading_model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        """Embed a list of texts, returning a numpy array of shape (N, 384)."""
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
        )

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single query string."""
        return self.model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]

    async def embed_chunks_with_progress(
        self,
        chunks: List[TextChunk],
        progress_callback: Optional[Callable] = None,
        batch_size: int = 64,
    ) -> List[dict]:
        """Embed all chunks with progress reporting.

        Returns list of dicts: {chunk, embedding, qdrant_payload}
        """
        results = []
        total = len(chunks)

        for batch_start in range(0, total, batch_size):
            batch = chunks[batch_start : batch_start + batch_size]
            texts = [c.text for c in batch]

            # Run in thread pool to avoid blocking event loop
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None, self.embed_texts, texts, batch_size
            )

            for i, chunk in enumerate(batch):
                results.append(
                    {
                        "chunk": chunk,
                        "embedding": embeddings[i].tolist(),
                    }
                )

            if progress_callback:
                processed = min(batch_start + batch_size, total)
                await progress_callback(
                    processed=processed,
                    total=total,
                    operation=f"Embedding chunks {processed}/{total}",
                )

            log.debug(
                "embedder.batch_complete",
                batch_start=batch_start,
                batch_size=len(batch),
                total=total,
            )

        log.info("embedder.all_complete", total_chunks=len(results))
        return results


# Singleton instance — loaded once, reused across requests
_embedder_instance: Optional[EmbeddingModule] = None


def get_embedder() -> EmbeddingModule:
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = EmbeddingModule()
    return _embedder_instance
