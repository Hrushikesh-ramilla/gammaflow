"""Document upload, processing status, and WebSocket progress endpoints.

Routes:
  POST /documents              — upload PDF, kick off async hybrid pipeline
  GET  /documents/{id}         — get document metadata
  GET  /documents/{id}/status  — poll processing status
  WS   /ws/processing/{job_id} — real-time per-page progress stream
"""

import asyncio
import json
import os
import uuid
from typing import Annotated

import aiofiles
import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.db.models import Document, User
from app.dependencies import get_db, get_embedder, get_qdrant
from app.ingestion.processor import HybridProcessor

log = structlog.get_logger()
router = APIRouter(prefix="/documents", tags=["ingestion"])

# ---------------------------------------------------------------------------
# In-memory job progress store (swap for Redis in production)
# ---------------------------------------------------------------------------
# Structure: { job_id: { "status": str, "pages_done": int, "total_pages": int,
#                         "warnings": list, "error": str|None } }
_job_store: dict[str, dict] = {}

# WebSocket connections per job_id
_ws_connections: dict[str, list[WebSocket]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_MIME = {"application/pdf"}
PDF_MAGIC = b"%PDF"


def _validate_pdf(content: bytes) -> None:
    """Raise HTTPException if the file is not a valid PDF."""
    if not content.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF")


async def _save_upload(upload: UploadFile) -> tuple[str, str]:
    """Save uploaded file to disk. Returns (filepath, original_filename)."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = ".pdf"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    content = await upload.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit",
        )
    _validate_pdf(content)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    return filepath, upload.filename or filename


async def _broadcast_progress(job_id: str, event: dict) -> None:
    """Send a progress event to all WebSocket clients watching this job."""
    disconnected = []
    for ws in _ws_connections.get(job_id, []):
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _ws_connections[job_id].remove(ws)


# ---------------------------------------------------------------------------
# Background processing task
# ---------------------------------------------------------------------------


async def _run_processing(
    job_id: str,
    document_id: str,
    filepath: str,
    document_role: str,
    user_id: str,
    syllabus_id: str | None,
) -> None:
    """Run the hybrid ingestion pipeline in the background."""
    from app.db.database import AsyncSessionLocal  # avoid circular import at module level

    log.info("processor.start", job_id=job_id, document_id=document_id)
    _job_store[job_id] = {
        "status": "processing",
        "pages_done": 0,
        "total_pages": 0,
        "warnings": [],
        "error": None,
    }

    try:
        embedder = get_embedder()
        qdrant = get_qdrant()
        processor = HybridProcessor(embedder=embedder, qdrant_client=qdrant)

        async def progress_cb(page_num: int, total: int, source_type: str, confidence: float | None):
            _job_store[job_id]["pages_done"] = page_num
            _job_store[job_id]["total_pages"] = total
            event = {
                "type": "page_processed",
                "page": page_num,
                "total": total,
                "source_type": source_type,
                "confidence": confidence,
            }
            if confidence is not None and confidence < settings.OCR_CONFIDENCE_WARNING:
                warning = f"Page {page_num} has low OCR confidence ({confidence:.0f}%)"
                _job_store[job_id]["warnings"].append(warning)
                event["warning"] = warning
            await _broadcast_progress(job_id, event)

        result = await processor.process_document(
            filepath=filepath,
            document_id=document_id,
            document_role=document_role,
            user_id=user_id,
            syllabus_id=syllabus_id,
            progress_callback=progress_cb,
        )

        # Update document status in DB
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    processing_status="completed",
                    total_pages=result.total_pages,
                    chunk_count=result.chunk_count,
                )
            )
            await db.commit()

        _job_store[job_id]["status"] = "completed"
        await _broadcast_progress(
            job_id,
            {
                "type": "complete",
                "total_pages": result.total_pages,
                "chunk_count": result.chunk_count,
                "warnings": _job_store[job_id]["warnings"],
            },
        )
        log.info(
            "processor.complete",
            job_id=job_id,
            pages=result.total_pages,
            chunks=result.chunk_count,
        )

    except Exception as exc:
        log.error("processor.failed", job_id=job_id, error=str(exc))
        _job_store[job_id]["status"] = "failed"
        _job_store[job_id]["error"] = str(exc)

        from app.db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(processing_status="failed")
            )
            await db.commit()

        await _broadcast_progress(job_id, {"type": "error", "message": str(exc)})
    finally:
        # Cleanup file after processing
        try:
            os.remove(filepath)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF file to process")],
    role: Annotated[str, Form(description="SYLLABUS | TEXTBOOK | NOTES")] = "TEXTBOOK",
    syllabus_id: Annotated[str | None, Form()] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF document. Returns a job_id for real-time progress tracking."""
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    if role not in {"SYLLABUS", "TEXTBOOK", "NOTES"}:
        raise HTTPException(status_code=400, detail="role must be SYLLABUS, TEXTBOOK, or NOTES")

    filepath, original_name = await _save_upload(file)

    document_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    document = Document(
        id=document_id,
        user_id=current_user.id,
        syllabus_id=syllabus_id,
        filename=original_name,
        role=role,
        processing_status="queued",
        job_id=job_id,
    )
    db.add(document)
    await db.flush()

    background_tasks.add_task(
        _run_processing,
        job_id=job_id,
        document_id=document_id,
        filepath=filepath,
        document_role=role,
        user_id=current_user.id,
        syllabus_id=syllabus_id,
    )

    log.info("ingestion.queued", document_id=document_id, job_id=job_id, role=role)
    return {"document_id": document_id, "job_id": job_id, "status": "queued"}


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return document metadata."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.user_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "role": doc.role,
        "processing_status": doc.processing_status,
        "total_pages": doc.total_pages,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at,
    }


@router.get("/{document_id}/status")
async def get_processing_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll processing status for a document."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.user_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    job_info = _job_store.get(doc.job_id, {})
    return {
        "document_id": document_id,
        "status": doc.processing_status,
        "pages_done": job_info.get("pages_done", 0),
        "total_pages": job_info.get("total_pages", doc.total_pages or 0),
        "warnings": job_info.get("warnings", []),
        "error": job_info.get("error"),
    }


@router.websocket("/ws/processing/{job_id}")
async def ws_processing(job_id: str, websocket: WebSocket):
    """WebSocket endpoint — streams per-page processing events to the client."""
    await websocket.accept()

    _ws_connections.setdefault(job_id, []).append(websocket)
    log.info("ws.client_connected", job_id=job_id)

    # If job already finished, send current state immediately
    if job_id in _job_store:
        job = _job_store[job_id]
        if job["status"] in ("completed", "failed"):
            event = {"type": "status", "status": job["status"], **job}
            await websocket.send_text(json.dumps(event))

    try:
        while True:
            # Keep connection alive; actual messages are pushed by background task
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        log.info("ws.client_disconnected", job_id=job_id)
        _ws_connections[job_id].remove(websocket)