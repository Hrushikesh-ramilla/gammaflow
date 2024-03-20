"""Qdrant collection definitions and initialization."""

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    VectorParams,
)

from app.config import settings

log = structlog.get_logger()

# Collection names
DOCUMENT_CHUNKS = "document_chunks"
PROBLEMS = "problems"
NOTE_TOPICS = "note_topics"

COLLECTIONS = {
    DOCUMENT_CHUNKS: {
        "size": settings.EMBEDDING_DIMENSION,
        "distance": Distance.COSINE,
        "payload_schema": {
            "user_id": "keyword",
            "syllabus_id": "keyword",
            "document_id": "keyword",
            "document_role": "keyword",
            "page_number": "integer",
            "char_start": "integer",
            "char_end": "integer",
            "chunk_index": "integer",
            "source_type": "keyword",  # 'PDF' | 'OCR'
            "ocr_confidence": "float",
            "text_preview": "text",
        },
    },
    PROBLEMS: {
        "size": settings.EMBEDDING_DIMENSION,
        "distance": Distance.COSINE,
        "payload_schema": {
            "user_id": "keyword",
            "syllabus_id": "keyword",
            "document_id": "keyword",
            "problem_id": "keyword",
            "page_number": "integer",
            "problem_number": "keyword",
        },
    },
    NOTE_TOPICS: {
        "size": settings.EMBEDDING_DIMENSION,
        "distance": Distance.COSINE,
        "payload_schema": {
            "user_id": "keyword",
            "syllabus_id": "keyword",
            "topic_text": "text",
            "source_page": "integer",
        },
    },
}


async def ensure_collections(client: AsyncQdrantClient) -> None:
    """Create Qdrant collections if they do not exist."""
    existing = {c.name for c in await client.get_collections().collections}

    for name, config in COLLECTIONS.items():
        if name not in existing:
            await client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=config["size"],
                    distance=config["distance"],
                ),
                hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=20000,
                    memmap_threshold=50000,
                ),
            )
            log.info("qdrant.collection_created", name=name)
        else:
            log.info("qdrant.collection_exists", name=name)
