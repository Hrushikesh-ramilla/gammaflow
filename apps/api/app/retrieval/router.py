"""Retrieval API endpoints — semantic search over ingested document chunks.

Routes:
  POST /retrieval/search  — search chunks by query with optional topic/doc filters
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.models import User
from app.dependencies import get_db, get_embedder, get_qdrant
from app.ingestion.embedder import EmbeddingModel
from app.retrieval.reranker import rerank
from app.retrieval.schemas import RetrievalResponse, SearchRequest, SearchResult
from app.retrieval.searcher import QdrantSearcher

log = structlog.get_logger()
router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
async def search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingModel = Depends(get_embedder),
    qdrant=Depends(get_qdrant),
    current_user: User = Depends(get_current_user),
):
    """Search ingested document chunks using semantic similarity.

    Optionally filter by syllabus, document role, or topic tag.
    Applies cross-encoder reranking if `use_reranking=True`.
    """
    # Embed the query
    try:
        query_embedding = embedder.embed_text(body.query)
    except Exception as exc:
        log.error("retrieval.embed_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Embedding failed") from exc

    # Search Qdrant — fetch more candidates if reranking is enabled
    candidate_k = body.top_k * 3 if body.use_reranking else body.top_k
    searcher = QdrantSearcher(client=qdrant)

    try:
        raw_results = await searcher.search(
            query_vector=query_embedding,
            user_id=current_user.id,
            syllabus_id=body.syllabus_id,
            document_ids=body.document_ids,
            document_role=body.document_role,
            topic_tag=body.topic_tag,
            top_k=candidate_k,
        )
    except Exception as exc:
        log.error("retrieval.qdrant_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Search failed") from exc

    # Rerank
    if body.use_reranking and raw_results:
        raw_results = rerank(body.query, raw_results, top_k=body.top_k)

    results = [
        SearchResult(
            chunk_id=r.get("chunk_id", ""),
            document_id=r.get("document_id", ""),
            document_role=r.get("document_role", ""),
            page_number=r.get("page_number", 0),
            text=r.get("text", ""),
            source_type=r.get("source_type", "PDF"),
            ocr_confidence=r.get("ocr_confidence"),
            char_start=r.get("char_start"),
            char_end=r.get("char_end"),
            score=r.get("score", 0.0),
            rerank_score=r.get("rerank_score"),
        )
        for r in raw_results
    ]

    return RetrievalResponse(query=body.query, results=results, total=len(results))
