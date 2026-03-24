"""Qdrant search module with metadata filtering and reranking."""

from typing import List, Optional

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, SearchRequest

from app.config import settings
from app.vector.collections import DOCUMENT_CHUNKS, PROBLEMS, NOTE_TOPICS

log = structlog.get_logger()


class QdrantSearcher:
    """Semantic search over document chunks with metadata filtering."""

    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def search_chunks(
        self,
        query_embedding: List[float],
        user_id: str,
        syllabus_id: str,
        topic_id: Optional[str] = None,
        document_role: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.3,
    ) -> List[dict]:
        """Search document chunks with optional topic and role filtering.

        Args:
            query_embedding: The query vector (384-dim)
            user_id: Filter by user (data isolation)
            syllabus_id: Filter by syllabus
            topic_id: Optional — filter chunks tagged to this topic
            document_role: Optional — 'TEXTBOOK' | 'NOTES' | None (all)
            limit: Number of results to return
            score_threshold: Minimum cosine similarity score

        Returns:
            List of dicts with chunk metadata and score
        """
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="syllabus_id", match=MatchValue(value=syllabus_id)),
        ]

        if document_role:
            must_conditions.append(
                FieldCondition(key="document_role", match=MatchValue(value=document_role))
            )

        search_filter = Filter(must=must_conditions)

        results = await self.client.search(
            collection_name=DOCUMENT_CHUNKS,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit * 2,  # over-fetch for reranking
            score_threshold=score_threshold,
            with_payload=True,
        )

        log.debug(
            "searcher.results",
            count=len(results),
            syllabus_id=syllabus_id,
            topic_id=topic_id,
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "text": r.payload.get("text", ""),
                "page_number": r.payload.get("page_number"),
                "source_type": r.payload.get("source_type", "PDF"),
                "ocr_confidence": r.payload.get("ocr_confidence", 1.0),
                "document_id": r.payload.get("document_id"),
                "document_role": r.payload.get("document_role"),
                "char_start": r.payload.get("char_start"),
                "char_end": r.payload.get("char_end"),
                "chunk_index": r.payload.get("chunk_index"),
            }
            for r in results
        ][:limit]

    async def search_problems(
        self,
        query_embedding: List[float],
        user_id: str,
        syllabus_id: str,
        limit: int = 10,
    ) -> List[dict]:
        """Search problems collection for ranking."""
        results = await self.client.search(
            collection_name=PROBLEMS,
            query_vector=query_embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    FieldCondition(key="syllabus_id", match=MatchValue(value=syllabus_id)),
                ]
            ),
            limit=limit,
            with_payload=True,
        )
        return [
            {
                "id": str(r.id),
                "score": r.score,
                "problem_id": r.payload.get("problem_id"),
                "page_number": r.payload.get("page_number"),
                "problem_number": r.payload.get("problem_number"),
            }
            for r in results
        ]

    async def upsert_chunks(
        self,
        chunks_with_embeddings: List[dict],
        user_id: str,
        syllabus_id: str,
        document_id: str,
        document_role: str,
    ) -> int:
        """Store chunk embeddings in Qdrant."""
        from qdrant_client.models import PointStruct
        import uuid

        points = []
        for item in chunks_with_embeddings:
            chunk = item["chunk"]
            embedding = item["embedding"]
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "user_id": user_id,
                        "syllabus_id": syllabus_id,
                        "document_id": document_id,
                        "document_role": document_role,
                        "page_number": chunk.page_number,
                        "char_start": chunk.char_start,
                        "char_end": chunk.char_end,
                        "chunk_index": chunk.chunk_index,
                        "source_type": chunk.source_type,
                        "ocr_confidence": chunk.ocr_confidence,
                        "text": chunk.text,
                        "text_preview": chunk.text[:100],
                    },
                )
            )

        if points:
            await self.client.upsert(
                collection_name=DOCUMENT_CHUNKS,
                points=points,
            )
            log.info("searcher.chunks_upserted", count=len(points))

        return len(points)
