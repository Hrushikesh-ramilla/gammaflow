"""Pydantic schemas for the ingestion pipeline."""

from typing import List, Optional
from pydantic import BaseModel, Field


class PageExtractionResult(BaseModel):
    """Result of processing a single PDF page."""

    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(..., description="Extracted or OCR'd text")
    source: str = Field(..., description="'PDF' for text extraction, 'OCR' for Tesseract")
    confidence: float = Field(default=1.0, description="OCR confidence (0-100), 1.0 for PDF")
    char_start: int = Field(default=0)
    char_end: int = Field(default=0)
    low_confidence_warning: bool = Field(default=False)


class ChunkSchema(BaseModel):
    """A single text chunk ready for embedding and Qdrant storage."""

    chunk_index: int
    text: str
    char_start: int
    char_end: int
    page_number: int
    source_type: str  # 'PDF' | 'OCR'
    ocr_confidence: float = 1.0
    token_estimate: int = 0


class DocumentIngestionRequest(BaseModel):
    """Request body for starting document ingestion."""

    document_id: str
    syllabus_id: str
    user_id: str
    role: str  # 'TEXTBOOK' | 'NOTES' | 'SYLLABUS'
    file_path: str


class IngestionStatusResponse(BaseModel):
    """Response for processing status endpoint."""

    document_id: str
    status: str  # 'pending' | 'processing' | 'completed' | 'failed'
    progress: int = Field(default=0, ge=0, le=100)
    current_operation: Optional[str] = None
    total_pages: Optional[int] = None
    processed_pages: Optional[int] = None
    ocr_pages: Optional[List[int]] = None
    low_confidence_pages: Optional[List[int]] = None
    error: Optional[str] = None


class OCRWarning(BaseModel):
    """Warning details for low-confidence OCR pages."""

    page_number: int
    confidence: float
    message: str
