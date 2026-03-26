"""Conversation endpoints — chat with SSE streaming.

Routes:
  POST /sessions               — create a new study session
  GET  /sessions/{id}          — get session details + message history
  POST /sessions/{id}/messages — send a message, stream the response (SSE)
  GET  /sessions/{id}/history  — get paginated message history
"""

import json
import uuid
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.conversation.cache import get_response_cache
from app.conversation.citation_parser import parse_citations
from app.conversation.fallback import LLMFallbackManager
from app.conversation.prompt_builder import PromptBuilder
from app.conversation.schemas import (
    MessageRequest,
    MessageResponse,
    SessionCreateRequest,
    SessionResponse,
)
from app.db.models import Document, Message, StudySession, Syllabus, Topic
from app.dependencies import get_db, get_embedder, get_llm, get_qdrant
from app.ingestion.embedder import EmbeddingModel
from app.retrieval.reranker import rerank
from app.retrieval.searcher import QdrantSearcher

log = structlog.get_logger()
router = APIRouter(prefix="/sessions", tags=["conversation"])


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new study session for a syllabus topic."""
    # Validate syllabus belongs to user
    syl_result = await db.execute(
        select(Syllabus).where(
            Syllabus.id == body.syllabus_id,
            Syllabus.user_id == current_user.id,
        )
    )
    if not syl_result.scalar_one_or_none():
        raise HTTPException(404, "Syllabus not found")

    session = StudySession(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        syllabus_id=body.syllabus_id,
        current_topic_id=body.topic_id,
        current_topic_name=body.topic_name,
        deviation_stack=json.dumps([]),
    )
    db.add(session)
    await db.flush()

    return SessionResponse(
        id=session.id,
        syllabus_id=session.syllabus_id,
        topic_id=session.current_topic_id,
        topic_name=session.current_topic_name,
        deviation_depth=0,
        message_count=0,
        created_at=session.created_at,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get session info including current deviation depth."""
    result = await db.execute(
        select(StudySession).where(
            StudySession.id == session_id,
            StudySession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    stack = json.loads(session.deviation_stack or "[]")
    msg_result = await db.execute(
        select(Message).where(Message.session_id == session_id)
    )
    messages = msg_result.scalars().all()

    return SessionResponse(
        id=session.id,
        syllabus_id=session.syllabus_id,
        topic_id=session.current_topic_id,
        topic_name=session.current_topic_name,
        deviation_depth=len(stack),
        message_count=len(messages),
        created_at=session.created_at,
    )


@router.get("/{session_id}/history")
async def get_history(
    session_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return paginated message history for a session."""
    result = await db.execute(
        select(StudySession).where(
            StudySession.id == session_id,
            StudySession.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Session not found")

    msgs = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    messages = msgs.scalars().all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": m.citations or [],
            "provider": m.llm_provider,
            "created_at": m.created_at,
        }
        for m in messages
    ]


# ---------------------------------------------------------------------------
# SSE message streaming
# ---------------------------------------------------------------------------


async def _sse_event(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


@router.post("/{session_id}/messages")
async def send_message(
    session_id: str,
    body: MessageRequest,
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingModel = Depends(get_embedder),
    qdrant=Depends(get_qdrant),
    llm: LLMFallbackManager = Depends(get_llm),
    current_user=Depends(get_current_user),
):
    """Send a user message and receive a streaming SSE response.

    The response is an event stream:
      token events → real-time text
      citation events → page references for PDF autoscroll
      complete event → final metadata (tokens, provider)
    """
    # 1. Load session
    sess_result = await db.execute(
        select(StudySession).where(
            StudySession.id == session_id,
            StudySession.user_id == current_user.id,
        )
    )
    session = sess_result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    # 2. Store user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    # 3. Retrieve relevant chunks
    query_embedding = embedder.embed_text(body.content)
    searcher = QdrantSearcher(client=qdrant)
    raw_chunks = await searcher.search(
        query_vector=query_embedding,
        user_id=current_user.id,
        syllabus_id=session.syllabus_id,
        top_k=20,
    )
    chunks = rerank(body.content, raw_chunks, top_k=5) if raw_chunks else []

    # 4. Check response cache
    cache = get_response_cache()
    topic_id = session.current_topic_id or "general"
    cached = cache.get(body.content, topic_id, question_embedding=query_embedding)
    if cached:
        log.info("conversation.cache_hit", session_id=session_id)

        async def _cached_stream() -> AsyncGenerator[str, None]:
            yield await _sse_event({"type": "token", "content": cached.text, "provider": cached.provider})
            for c in cached.citations:
                yield await _sse_event({"type": "citation", **c})
            yield await _sse_event({"type": "complete", "provider": cached.provider, "cached": True})

        return StreamingResponse(_cached_stream(), media_type="text/event-stream")

    # 5. Build prompt
    hist_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .limit(settings.LAST_N_MESSAGES * 2)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in hist_result.scalars().all()
        if m.id != user_msg.id
    ]

    builder = PromptBuilder()
    system_prompt = builder.build_system_prompt(
        topic_name=session.current_topic_name or "General",
        estimated_depth="intermediate",
        prerequisites=[],
        chunks=chunks,
    )
    messages = builder.build_messages(
        conversation_history=history,
        current_message=body.content,
        session_summary=session.session_summary,
    )

    # 6. Stream response
    full_text = []
    provider_used = "unknown"
    tokens_used = 0

    async def _stream() -> AsyncGenerator[str, None]:
        nonlocal provider_used, tokens_used

        try:
            async for event in llm.stream_response(
                messages=messages,
                system_prompt=system_prompt,
                retrieved_chunks=chunks,
            ):
                if event["type"] == "token":
                    full_text.append(event["content"])
                    provider_used = event.get("provider", "unknown")
                    yield await _sse_event(event)

                elif event["type"] == "provider_switched":
                    yield await _sse_event(event)

                elif event["type"] == "complete":
                    tokens_used = event.get("tokens_used", 0)
                    provider_used = event.get("provider", provider_used)

                    # Parse citations from full assembled text
                    assembled = "".join(full_text)
                    parsed_citations = parse_citations(assembled)
                    for cit in parsed_citations:
                        # Match citation to chunk metadata for char offsets
                        matching_chunk = next(
                            (
                                c
                                for c in chunks
                                if c.get("page_number") == cit.page_number
                            ),
                            None,
                        )
                        cit_event = {
                            "type": "citation",
                            "page": cit.page_number,
                            "doc": cit.document_name,
                            "source": matching_chunk.get("source_type", "PDF") if matching_chunk else "PDF",
                            "char_start": matching_chunk.get("char_start") if matching_chunk else None,
                            "char_end": matching_chunk.get("char_end") if matching_chunk else None,
                        }
                        yield await _sse_event(cit_event)

                    # Persist assistant message
                    assistant_msg_id = str(uuid.uuid4())
                    try:
                        from app.db.database import AsyncSessionLocal

                        async with AsyncSessionLocal() as save_db:
                            asst_msg = Message(
                                id=assistant_msg_id,
                                session_id=session_id,
                                role="assistant",
                                content=assembled,
                                citations=[
                                    {"page": c.page_number, "doc": c.document_name}
                                    for c in parsed_citations
                                ],
                                llm_provider=provider_used,
                                tokens_used=tokens_used,
                            )
                            save_db.add(asst_msg)
                            await save_db.commit()
                    except Exception as save_err:
                        log.error("conversation.save_failed", error=str(save_err))

                    # Store in cache
                    cache.put(
                        question=body.content,
                        topic_id=topic_id,
                        text=assembled,
                        citations=[
                            {"page": c.page_number, "doc": c.document_name}
                            for c in parsed_citations
                        ],
                        provider=provider_used,
                        question_embedding=query_embedding,
                    )

                    yield await _sse_event(
                        {
                            "type": "complete",
                            "provider": provider_used,
                            "tokens_used": tokens_used,
                            "message_id": assistant_msg_id,
                        }
                    )

                elif event["type"] == "fallback_to_chunks":
                    # Both LLMs failed — return raw chunks with disclaimer
                    text = event.get("disclaimer", "")
                    for chunk in event.get("chunks", []):
                        text += f"\n\n[Page {chunk.get('page_number')}] {chunk.get('text', '')[:300]}..."
                    yield await _sse_event({"type": "token", "content": text, "provider": "fallback"})
                    yield await _sse_event({"type": "complete", "provider": "fallback", "tokens_used": 0})

        except Exception as exc:
            log.error("conversation.stream_error", error=str(exc))
            yield await _sse_event({"type": "error", "message": str(exc)})

    return StreamingResponse(_stream(), media_type="text/event-stream")
