"""Pydantic schemas for note-to-textbook mapping."""

from typing import List, Optional
from enum import Enum

from pydantic import BaseModel


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"      # > 0.80
    MEDIUM = "MEDIUM"  # 0.60 – 0.80
    LOW = "LOW"        # < 0.60


class MappingResult(BaseModel):
    note_chunk_id: str
    note_page_number: int
    textbook_chunk_id: str
    textbook_page_number: int
    similarity_score: float
    confidence: ConfidenceLevel


class MappingComputeRequest(BaseModel):
    syllabus_id: str
    note_document_id: str
    textbook_document_id: str


class MappingResponse(BaseModel):
    syllabus_id: str
    mappings: List[MappingResult]
    total: int
    high_count: int
    medium_count: int
    low_count: int
