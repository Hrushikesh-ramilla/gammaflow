"""SYL FastAPI — main application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.db.database import engine, Base
from app.vector.client import get_qdrant_client
from app.vector.collections import ensure_collections
from app.ingestion.router import router as ingestion_router
from app.retrieval.router import router as retrieval_router
from app.syllabus.router import router as syllabus_router
from app.problems.router import router as problems_router
from app.mapping.router import router as mapping_router
from app.conversation.router import router as conversation_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    log.info("syl_api.starting", environment=settings.ENVIRONMENT)

    # Ensure DB tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("syl_api.db_ready")

    # Ensure Qdrant collections exist
    client = get_qdrant_client()
    await ensure_collections(client)
    log.info("syl_api.qdrant_ready")

    yield

    log.info("syl_api.shutting_down")
    await engine.dispose()


app = FastAPI(
    title="SYL API",
    description="Syllabus-aware AI study engine — ML pipeline and RAG",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(ingestion_router, prefix="/api/v1", tags=["ingestion"])
app.include_router(retrieval_router, prefix="/api/v1", tags=["retrieval"])
app.include_router(syllabus_router, prefix="/api/v1", tags=["syllabus"])
app.include_router(problems_router, prefix="/api/v1", tags=["problems"])
app.include_router(mapping_router, prefix="/api/v1", tags=["mapping"])
app.include_router(conversation_router, prefix="/api/v1", tags=["conversation"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "syl-api", "version": "1.0.0"}
