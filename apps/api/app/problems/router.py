"""Problems API endpoints.

Routes:
  POST /problems/extract              — extract problems from a document
  GET  /topics/{topic_id}/problems    — list ranked problems for a topic
  GET  /syllabuses/{id}/problems      — all problems for a syllabus (with tier filter)
  PATCH /problems/{id}/progress       — update user's progress on a problem
"""

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.models import Document, Problem, ProblemProgress, Topic
from app.dependencies import get_db, get_embedder, get_qdrant
from app.ingestion.embedder import EmbeddingModel
from app.problems.extractor import ProblemExtractor
from app.problems.ranker import ProblemRanker
from app.problems.schemas import (
    ExtractionRequest,
    ProblemProgressUpdate,
    ProblemWithProgressSchema,
    TierEnum,
)
from app.retrieval.searcher import QdrantSearcher

log = structlog.get_logger()
router = APIRouter(tags=["problems"])


# ---------------------------------------------------------------------------
# Background extraction task
# ---------------------------------------------------------------------------


async def _extract_and_rank_background(
    document_id: str,
    syllabus_id: str,
    user_id: str,
    chapter: Optional[str],
) -> None:
    """Background task: extract problems from document, rank against topics, persist."""
    from app.db.database import AsyncSessionLocal
    from app.vector.client import get_qdrant_client
    from app.ingestion.embedder import EmbeddingModel

    log.info("problems.bg_start", document_id=document_id)

    async with AsyncSessionLocal() as db:
        # Get document
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            log.error("problems.bg_document_not_found", document_id=document_id)
            return

        # Get chunks from Qdrant
        qdrant = get_qdrant_client()
        searcher = QdrantSearcher(client=qdrant)
        embedder = EmbeddingModel()

        try:
            # Search with a broad query to get document chunks
            query_vec = embedder.embed_text("problem exercise question")
            chunks = await searcher.search(
                query_vector=query_vec,
                user_id=user_id,
                syllabus_id=syllabus_id,
                document_ids=[document_id],
                top_k=50,
            )
        except Exception as exc:
            log.error("problems.bg_search_failed", error=str(exc))
            chunks = []

        # Extract problems via Claude Haiku
        extractor = ProblemExtractor()
        raw_problems = extractor.extract_from_chunks(chunks, chapter=chapter)
        if not raw_problems:
            log.info("problems.bg_no_problems_found", document_id=document_id)
            return

        # Get topic embeddings for ranking
        topic_result = await db.execute(
            select(Topic).where(Topic.syllabus_id == syllabus_id)
        )
        topics = topic_result.scalars().all()
        topic_texts = [f"{t.name} {t.description or ''}" for t in topics]
        topic_embeddings = [embedder.embed_text(t) for t in topic_texts]

        # Embed problems and rank
        problem_texts = [p["problem_text"] for p in raw_problems]
        problem_embeddings = [embedder.embed_text(t) for t in problem_texts]

        ranker = ProblemRanker()
        ranked = ranker.rank(raw_problems, problem_embeddings, topic_embeddings)

        # Persist to DB
        for p in ranked:
            problem = Problem(
                id=p["id"],
                document_id=document_id,
                problem_number=p.get("problem_number"),
                problem_text=p["problem_text"],
                page_number=p["page_number"],
                chapter=p.get("chapter"),
                rank_tier=p.get("rank_tier"),
                similarity_score=p.get("similarity_score"),
            )
            db.add(problem)

        await db.commit()
        log.info("problems.bg_complete", count=len(ranked), document_id=document_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/problems/extract", status_code=202)
async def extract_problems(
    body: ExtractionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Kick off background problem extraction for a document.

    Extraction → embedding → ranking against syllabus topics → DB persist.
    """
    # Validate document
    doc_result = await db.execute(
        select(Document).where(
            Document.id == body.document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(404, "Document not found")
    if document.processing_status != "completed":
        raise HTTPException(400, "Document must finish processing before extracting problems")

    background_tasks.add_task(
        _extract_and_rank_background,
        document_id=body.document_id,
        syllabus_id=body.syllabus_id,
        user_id=current_user.id,
        chapter=body.chapter,
    )

    return {"status": "queued", "document_id": body.document_id}


@router.get("/syllabuses/{syllabus_id}/problems")
async def list_problems(
    syllabus_id: str,
    tier: Optional[TierEnum] = Query(default=None, description="Filter by tier"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all problems for a syllabus, optionally filtered by tier."""
    # Get all document IDs for this syllabus
    doc_result = await db.execute(
        select(Document).where(
            Document.syllabus_id == syllabus_id,
            Document.user_id == current_user.id,
        )
    )
    doc_ids = [d.id for d in doc_result.scalars().all()]
    if not doc_ids:
        return []

    # Query problems
    query = select(Problem).where(Problem.document_id.in_(doc_ids))
    if tier:
        query = query.where(Problem.rank_tier == tier.value)
    query = query.order_by(Problem.similarity_score.desc().nullslast()).limit(limit)

    result = await db.execute(query)
    problems = result.scalars().all()

    # Fetch user's progress for these problems
    problem_ids = [p.id for p in problems]
    prog_result = await db.execute(
        select(ProblemProgress).where(
            ProblemProgress.problem_id.in_(problem_ids),
            ProblemProgress.user_id == current_user.id,
        )
    )
    progress_map = {pp.problem_id: pp.status for pp in prog_result.scalars().all()}

    return [
        {
            "id": p.id,
            "document_id": p.document_id,
            "problem_number": p.problem_number,
            "problem_text": p.problem_text,
            "page_number": p.page_number,
            "chapter": p.chapter,
            "rank_tier": p.rank_tier,
            "similarity_score": p.similarity_score,
            "user_status": progress_map.get(p.id, "todo"),
        }
        for p in problems
    ]


@router.patch("/problems/{problem_id}/progress")
async def update_problem_progress(
    problem_id: str,
    body: ProblemProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update the user's progress on a problem (todo → in_progress → done)."""
    # Verify problem exists
    prob_result = await db.execute(select(Problem).where(Problem.id == problem_id))
    if not prob_result.scalar_one_or_none():
        raise HTTPException(404, "Problem not found")

    # Upsert progress record
    prog_result = await db.execute(
        select(ProblemProgress).where(
            ProblemProgress.problem_id == problem_id,
            ProblemProgress.user_id == current_user.id,
        )
    )
    progress = prog_result.scalar_one_or_none()

    if progress:
        progress.status = body.status.value
    else:
        progress = ProblemProgress(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            problem_id=problem_id,
            status=body.status.value,
        )
        db.add(progress)

    await db.flush()
    return {"problem_id": problem_id, "status": body.status.value}
