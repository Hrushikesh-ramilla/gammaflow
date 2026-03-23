"""Dependency injection container for FastAPI.

Provides get_* functions to be used with FastAPI's Depends() system.
All expensive resources (DB sessions, Qdrant client, embedding model,
LLM manager) are managed here with caching where appropriate.
"""

from typing import AsyncGenerator

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.vector.client import get_qdrant_client
from app.ingestion.embedder import EmbeddingModel
from app.conversation.fallback import LLMFallbackManager
from app.conversation.cache import get_response_cache, ResponseCache

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session, committing on success or rolling back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------


def get_qdrant():
    """Return the cached Qdrant async client."""
    return get_qdrant_client()


# ---------------------------------------------------------------------------
# Embedding model (singleton — loaded once, reused across requests)
# ---------------------------------------------------------------------------

_embedding_model: EmbeddingModel | None = None


def get_embedder() -> EmbeddingModel:
    """Return the singleton embedding model (loaded lazily on first call)."""
    global _embedding_model
    if _embedding_model is None:
        log.info("dependencies.loading_embedding_model")
        _embedding_model = EmbeddingModel()
    return _embedding_model


# ---------------------------------------------------------------------------
# LLM fallback manager (singleton)
# ---------------------------------------------------------------------------

_fallback_manager: LLMFallbackManager | None = None


def get_llm() -> LLMFallbackManager:
    """Return the singleton LLM fallback manager."""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = LLMFallbackManager()
    return _fallback_manager


# ---------------------------------------------------------------------------
# Response cache (singleton)
# ---------------------------------------------------------------------------


def get_cache() -> ResponseCache:
    """Return the singleton response cache."""
    return get_response_cache()
