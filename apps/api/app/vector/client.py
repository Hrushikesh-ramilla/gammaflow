"""Qdrant vector database client wrapper."""

from functools import lru_cache

from qdrant_client import AsyncQdrantClient

from app.config import settings


@lru_cache
def get_qdrant_client() -> AsyncQdrantClient:
    """Return a cached Qdrant async client."""
    if settings.QDRANT_API_KEY:
        return AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=30,
        )
    return AsyncQdrantClient(
        url=settings.QDRANT_URL,
        timeout=30,
    )
