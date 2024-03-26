"""Response cache with semantic deduplication.

Same question asked multiple times? Answer once, reuse.
Keyed by: topic_id + question embedding (cosine > 0.95 = cache hit).
"""

import hashlib
import json
import time
from typing import List, Optional

import numpy as np
import structlog

log = structlog.get_logger()

CACHE_TTL_SECONDS = 86400  # 24 hours


class CachedResponse:
    def __init__(self, text: str, citations: List[dict], provider: str, created_at: float):
        self.text = text
        self.citations = citations
        self.provider = provider
        self.created_at = created_at

    def is_expired(self) -> bool:
        return time.time() - self.created_at > CACHE_TTL_SECONDS


class ResponseCache:
    """In-memory response cache with exact and semantic match.

    For production, swap the dict for Redis with serialization.
    """

    def __init__(self, semantic_threshold: float = 0.95):
        self.threshold = semantic_threshold
        self._exact: dict[str, CachedResponse] = {}
        self._semantic: list[dict] = []  # list of {key, embedding, response}

    def _exact_key(self, question: str, topic_id: str) -> str:
        return hashlib.sha256(f"{topic_id}:{question.strip().lower()}".encode()).hexdigest()

    def get(
        self,
        question: str,
        topic_id: str,
        question_embedding: Optional[List[float]] = None,
    ) -> Optional[CachedResponse]:
        """Check exact match first, then semantic match."""
        key = self._exact_key(question, topic_id)

        # Exact match
        if key in self._exact:
            resp = self._exact[key]
            if not resp.is_expired():
                log.debug("cache.exact_hit", topic_id=topic_id)
                return resp
            else:
                del self._exact[key]

        # Semantic match
        if question_embedding is not None:
            q_vec = np.array(question_embedding)
            for entry in self._semantic:
                if entry.get("topic_id") != topic_id:
                    continue
                if entry["response"].is_expired():
                    continue
                cached_vec = np.array(entry["embedding"])
                similarity = float(np.dot(q_vec, cached_vec))
                if similarity >= self.threshold:
                    log.debug(
                        "cache.semantic_hit",
                        similarity=round(similarity, 3),
                        topic_id=topic_id,
                    )
                    return entry["response"]

        return None

    def put(
        self,
        question: str,
        topic_id: str,
        text: str,
        citations: List[dict],
        provider: str,
        question_embedding: Optional[List[float]] = None,
    ) -> None:
        """Store a response in both exact and semantic caches."""
        key = self._exact_key(question, topic_id)
        response = CachedResponse(
            text=text,
            citations=citations,
            provider=provider,
            created_at=time.time(),
        )
        self._exact[key] = response

        if question_embedding is not None:
            self._semantic.append(
                {
                    "key": key,
                    "topic_id": topic_id,
                    "embedding": question_embedding,
                    "response": response,
                }
            )

        log.debug("cache.stored", topic_id=topic_id, provider=provider)

    def invalidate_syllabus(self, syllabus_id: str) -> None:
        """Invalidate all cached responses for a syllabus (e.g., new doc uploaded)."""
        self._exact.clear()
        self._semantic = [e for e in self._semantic if e.get("syllabus_id") != syllabus_id]
        log.info("cache.invalidated", syllabus_id=syllabus_id)


# Singleton
_cache_instance: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCache()
    return _cache_instance
