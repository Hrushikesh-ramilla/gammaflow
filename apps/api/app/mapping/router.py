"""Note-to-textbook mapping API endpoints.

Routes:
  POST /mapping/compute               — compute and persist mappings for a syllabus
  GET  /syllabuses/{id}/mappings      — get mappings for a syllabus
  GET  /syllabuses/{id}/mappings/page/{page} — get mappings for a specific notes page
"""

import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.models import Document, NoteTextbookMapping
from app.dependencies import get_db
from app.mapping.mapper import NoteTextbookMapper
from app.mapping.schemas import (
    ConfidenceLevel,
    MappingComputeRequest,
    MappingResponse,
    MappingResult,
)

log = structlog.get_logger()
router = APIRouter(tags=["mapping"])


async def _compute_and_persist(
    syllabus_id: str,
    note_document_id: str,
    textbook_document_id: str,
    user_id: str,
) -> None:
    """Background task: compute note→textbook mappings and persist."""
    from app.db.database import AsyncSessionLocal
    from app.vector.client import get_qdrant_client
    from app.ingestion.embedder import EmbeddingModel
    from app.retrieval.searcher import QdrantSearcher

    log.info("mapping.bg_start", syllabus_id=syllabus_id)

    async with AsyncSessionLocal() as db:
        try:
            qdrant = get_qdrant_client()
            embedder = EmbeddingModel()
            searcher = QdrantSearcher(client=qdrant)

            generic_vec = embedder.embed_text("lecture notes textbook chapter")

            note_chunks = await searcher.search(
                query_vector=generic_vec,
                user_id=user_id,
                syllabus_id=syllabus_id,
                document_ids=[note_document_id],
                top_k=100,
            )
            textbook_chunks = await searcher.search(
                query_vector=generic_vec,
                user_id=user_id,
                syllabus_id=syllabus_id,
                document_ids=[textbook_document_id],
                top_k=100,
            )

            if not note_chunks or not textbook_chunks:
                log.warning("mapping.bg_no_chunks")
                return

            note_embeddings = [embedder.embed_text(c["text"]) for c in note_chunks]
            textbook_embeddings = [embedder.embed_text(c["text"]) for c in textbook_chunks]

            mapper = NoteTextbookMapper()
            mappings = mapper.compute_mappings(
                note_chunks=note_chunks,
                textbook_chunks=textbook_chunks,
                note_embeddings=note_embeddings,
                textbook_embeddings=textbook_embeddings,
            )

            for m in mappings:
                record = NoteTextbookMapping(
                    id=str(uuid.uuid4()),
                    note_chunk_qdrant_id=m["note_chunk_id"],
                    textbook_chunk_qdrant_id=m["textbook_chunk_id"],
                    similarity_score=m["similarity_score"],
                    confidence=m["confidence"],
                    syllabus_id=syllabus_id,
                )
                db.add(record)

            await db.commit()
            log.info("mapping.bg_complete", count=len(mappings))

        except Exception as exc:
            log.error("mapping.bg_failed", error=str(exc))


@router.post("/mapping/compute", status_code=202)
async def compute_mappings(
    body: MappingComputeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger async computation of note-to-textbook mappings."""
    for doc_id in [body.note_document_id, body.textbook_document_id]:
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == current_user.id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(404, f"Document {doc_id} not found")

    background_tasks.add_task(
        _compute_and_persist,
        syllabus_id=body.syllabus_id,
        note_document_id=body.note_document_id,
        textbook_document_id=body.textbook_document_id,
        user_id=current_user.id,
    )
    return {"status": "queued", "syllabus_id": body.syllabus_id}


@router.get("/syllabuses/{syllabus_id}/mappings", response_model=MappingResponse)
async def get_mappings(
    syllabus_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all computed mappings for a syllabus."""
    result = await db.execute(
        select(NoteTextbookMapping).where(
            NoteTextbookMapping.syllabus_id == syllabus_id
        )
    )
    records = result.scalars().all()

    mapping_results = [
        MappingResult(
            note_chunk_id=r.note_chunk_qdrant_id,
            note_page_number=0,  # page metadata stored in Qdrant payload
            textbook_chunk_id=r.textbook_chunk_qdrant_id,
            textbook_page_number=0,
            similarity_score=r.similarity_score,
            confidence=ConfidenceLevel(r.confidence) if r.confidence else ConfidenceLevel.LOW,
        )
        for r in records
    ]

    counts = {c: sum(1 for m in mapping_results if m.confidence == c) for c in ConfidenceLevel}
    return MappingResponse(
        syllabus_id=syllabus_id,
        mappings=mapping_results,
        total=len(mapping_results),
        high_count=counts.get(ConfidenceLevel.HIGH, 0),
        medium_count=counts.get(ConfidenceLevel.MEDIUM, 0),
        low_count=counts.get(ConfidenceLevel.LOW, 0),
    )
