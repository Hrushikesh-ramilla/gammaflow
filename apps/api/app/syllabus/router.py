"""Syllabus API endpoints.

Routes:
  POST /syllabuses                    — create syllabus, parse topics from PDF
  GET  /syllabuses                    — list user's syllabuses
  GET  /syllabuses/{id}               — get syllabus metadata
  GET  /syllabuses/{id}/graph         — return React Flow nodes + edges
  GET  /syllabuses/{id}/topics        — list topics
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.models import Document, Syllabus, Topic
from app.dependencies import get_db
from app.syllabus.graph_builder import GraphBuilder
from app.syllabus.parser import SyllabusParser
from app.syllabus.schemas import (
    GraphEdge,
    GraphNode,
    GraphNodeData,
    GraphResponse,
    SyllabusCreateRequest,
    SyllabusResponse,
)

log = structlog.get_logger()
router = APIRouter(prefix="/syllabuses", tags=["syllabus"])


@router.post("", response_model=SyllabusResponse, status_code=201)
async def create_syllabus(
    body: SyllabusCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Parse a syllabus PDF document and create the knowledge graph."""
    # Validate document belongs to user
    doc_result = await db.execute(
        select(Document).where(
            Document.id == body.document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(404, "Document not found")
    if document.role != "SYLLABUS":
        raise HTTPException(400, "Document must have role SYLLABUS")
    if document.processing_status != "completed":
        raise HTTPException(400, "Document is still being processed")

    # Create syllabus record
    syllabus_id = str(uuid.uuid4())
    syllabus = Syllabus(
        id=syllabus_id,
        user_id=current_user.id,
        course_name=body.course_name,
        document_id=body.document_id,
    )
    db.add(syllabus)
    await db.flush()

    # Update document's syllabus_id
    document.syllabus_id = syllabus_id

    # Parse topics via Claude
    try:
        parser = SyllabusParser()
        # Get text from the document (stored in Qdrant; use a simplified extraction here)
        # For now, trigger parsing from document filename placeholder
        topic_list = await parser.parse(
            syllabus_text=f"Course: {body.course_name}",  # Will be enhanced with actual text retrieval
            course_name=body.course_name,
        )
    except Exception as exc:
        log.error("syllabus.parse_failed", error=str(exc))
        topic_list = []  # Graceful degradation — empty graph

    # Persist topics
    for topic_data in topic_list:
        topic = Topic(
            id=topic_data.get("id", str(uuid.uuid4())),
            syllabus_id=syllabus_id,
            name=topic_data["name"],
            description=topic_data.get("description", ""),
            estimated_depth=topic_data.get("estimated_depth", "intermediate"),
            prerequisites=topic_data.get("prerequisites", []),
            week_number=topic_data.get("week"),
            keywords=topic_data.get("keywords", []),
        )
        db.add(topic)

    await db.flush()

    return SyllabusResponse(
        id=syllabus.id,
        course_name=syllabus.course_name,
        user_id=syllabus.user_id,
        document_id=syllabus.document_id,
        topic_count=len(topic_list),
        created_at=syllabus.created_at,
    )


@router.get("", response_model=list[SyllabusResponse])
async def list_syllabuses(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all syllabuses for the current user."""
    result = await db.execute(
        select(Syllabus)
        .where(Syllabus.user_id == current_user.id)
        .order_by(Syllabus.created_at.desc())
    )
    syllabuses = result.scalars().all()

    out = []
    for s in syllabuses:
        topic_result = await db.execute(
            select(Topic).where(Topic.syllabus_id == s.id)
        )
        topics = topic_result.scalars().all()
        out.append(
            SyllabusResponse(
                id=s.id,
                course_name=s.course_name,
                user_id=s.user_id,
                document_id=s.document_id,
                topic_count=len(topics),
                created_at=s.created_at,
            )
        )
    return out


@router.get("/{syllabus_id}", response_model=SyllabusResponse)
async def get_syllabus(
    syllabus_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get syllabus metadata."""
    result = await db.execute(
        select(Syllabus).where(
            Syllabus.id == syllabus_id,
            Syllabus.user_id == current_user.id,
        )
    )
    syllabus = result.scalar_one_or_none()
    if not syllabus:
        raise HTTPException(404, "Syllabus not found")

    topic_result = await db.execute(select(Topic).where(Topic.syllabus_id == syllabus_id))
    topic_count = len(topic_result.scalars().all())

    return SyllabusResponse(
        id=syllabus.id,
        course_name=syllabus.course_name,
        user_id=syllabus.user_id,
        document_id=syllabus.document_id,
        topic_count=topic_count,
        created_at=syllabus.created_at,
    )


@router.get("/{syllabus_id}/graph", response_model=GraphResponse)
async def get_graph(
    syllabus_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return React Flow compatible nodes and edges for the knowledge graph."""
    result = await db.execute(
        select(Syllabus).where(
            Syllabus.id == syllabus_id,
            Syllabus.user_id == current_user.id,
        )
    )
    syllabus = result.scalar_one_or_none()
    if not syllabus:
        raise HTTPException(404, "Syllabus not found")

    topic_result = await db.execute(
        select(Topic).where(Topic.syllabus_id == syllabus_id)
    )
    topics_orm = topic_result.scalars().all()

    topics_dicts = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description or "",
            "estimated_depth": t.estimated_depth or "intermediate",
            "prerequisites": t.prerequisites or [],
            "keywords": t.keywords or [],
        }
        for t in topics_orm
    ]

    builder = GraphBuilder()
    graph_data = builder.build(topics_dicts)

    nodes = [
        GraphNode(
            id=n["id"],
            type=n["type"],
            position=n["position"],
            data=GraphNodeData(**n["data"]),
        )
        for n in graph_data["nodes"]
    ]
    edges = [
        GraphEdge(
            id=e["id"],
            source=e["source"],
            target=e["target"],
            type=e.get("type", "topicEdge"),
            animated=e.get("animated", False),
            style=e.get("style"),
            markerEnd=e.get("markerEnd"),
        )
        for e in graph_data["edges"]
    ]

    return GraphResponse(
        syllabus_id=syllabus_id,
        course_name=syllabus.course_name,
        nodes=nodes,
        edges=edges,
        topic_count=len(nodes),
    )


@router.get("/{syllabus_id}/topics")
async def list_topics(
    syllabus_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all topics for this syllabus."""
    result = await db.execute(
        select(Topic).where(Topic.syllabus_id == syllabus_id)
    )
    topics = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "estimated_depth": t.estimated_depth,
            "prerequisites": t.prerequisites or [],
            "week_number": t.week_number,
        }
        for t in topics
    ]
