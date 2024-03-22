"""Hybrid ingestion processor — orchestrates the full per-page pipeline.

Flow per page:
  detect → TEXT: extract via PyMuPDF
  detect → SCANNED: preprocess → Tesseract OCR → clean
  → adaptive chunk → embed → store in Qdrant
"""

import asyncio
from pathlib import Path
from typing import Callable, Optional

import fitz
import structlog

from app.config import settings
from app.ingestion.chunker import AdaptiveChunker, TextChunk
from app.ingestion.detector import PageDetector, PageType
from app.ingestion.extractor import PDFExtractor
from app.ingestion.ocr import TesseractOCR
from app.ingestion.schemas import PageExtractionResult
from app.ingestion.text_cleaner import OCRTextCleaner

log = structlog.get_logger()


class HybridIngestionProcessor:
    """Orchestrates the complete hybrid PDF ingestion pipeline.

    Supports:
    - Text-only PDFs
    - Scanned-only PDFs
    - Hybrid PDFs (per-page detection — the common real-world case)

    Resumable: tracks last_processed_chunk so failed jobs can resume.
    """

    def __init__(self):
        self.detector = PageDetector()
        self.extractor = PDFExtractor()
        self.ocr = TesseractOCR()
        self.cleaner = OCRTextCleaner()
        self.chunker = AdaptiveChunker()

    async def process_document(
        self,
        file_path: str,
        document_id: str,
        syllabus_id: str,
        user_id: str,
        document_role: str,
        progress_callback: Optional[Callable] = None,
        resume_from_chunk: int = 0,
    ) -> dict:
        """Process a PDF document through the full hybrid pipeline.

        Args:
            file_path: Path to the uploaded PDF
            document_id: PostgreSQL document ID
            syllabus_id: Syllabus this document belongs to
            user_id: Owning user ID
            document_role: 'TEXTBOOK' | 'NOTES' | 'SYLLABUS'
            progress_callback: Optional async callable(page, total, operation, ocr_warnings)
            resume_from_chunk: Skip chunks before this index (for resuming)

        Returns:
            dict with total_chunks, ocr_pages, low_confidence_pages
        """
        doc = fitz.open(file_path)
        total_pages = len(doc)
        log.info(
            "processor.started",
            document_id=document_id,
            total_pages=total_pages,
            role=document_role,
        )

        # Step 1: Classify all pages
        page_classifications = self.detector.classify_document(doc)
        ocr_pages = [p["page_number"] for p in page_classifications if p["page_type"] == PageType.SCANNED]
        low_confidence_pages = []

        # Step 2: Extract text per page
        extracted_pages: list[PageExtractionResult] = []
        cumulative_offset = 0

        for i, page_info in enumerate(page_classifications):
            page = doc[i]
            page_num = page_info["page_number"]

            if page_info["page_type"] == PageType.TEXT:
                # Direct PyMuPDF extraction
                ep = self.extractor.extract_page(page, cumulative_offset)
                raw_text = ep.text
                source = "PDF"
                confidence = 1.0
                low_conf_warning = False
            else:
                # OCR pipeline
                ocr_result = await asyncio.get_event_loop().run_in_executor(
                    None, self.ocr.ocr_page, page, cumulative_offset
                )
                raw_text = self.cleaner.clean(ocr_result.text)
                source = "OCR"
                confidence = ocr_result.confidence
                low_conf_warning = ocr_result.low_confidence_warning
                if low_conf_warning:
                    low_confidence_pages.append(page_num)

            cumulative_offset += len(raw_text)
            extracted_pages.append(
                PageExtractionResult(
                    page_number=page_num,
                    text=raw_text,
                    source=source,
                    confidence=confidence,
                    char_start=cumulative_offset - len(raw_text),
                    char_end=cumulative_offset,
                    low_confidence_warning=low_conf_warning,
                )
            )

            if progress_callback:
                await progress_callback(
                    page=page_num,
                    total=total_pages,
                    operation=f"Extracting page {page_num} ({source})",
                    ocr_warnings=low_confidence_pages,
                )

        doc.close()

        # Step 3: Chunk all pages
        all_chunks: list[TextChunk] = []
        chunk_idx = 0
        for ep in extracted_pages:
            chunks = self.chunker.chunk_page(
                text=ep.text,
                page_number=ep.page_number,
                source_type=ep.source,
                ocr_confidence=ep.confidence,
                char_base_offset=ep.char_start,
                chunk_index_start=chunk_idx,
            )
            all_chunks.extend(chunks)
            chunk_idx += len(chunks)

        log.info(
            "processor.chunking_complete",
            document_id=document_id,
            total_chunks=len(all_chunks),
        )

        # Step 4: Filter already-processed chunks (for resume)
        chunks_to_embed = [c for c in all_chunks if c.chunk_index >= resume_from_chunk]

        # Steps 5 & 6 (embed + store) are handled by the embedder module
        # which is called by the background task worker

        return {
            "extracted_pages": extracted_pages,
            "all_chunks": chunks_to_embed,
            "total_chunks": len(all_chunks),
            "ocr_pages": ocr_pages,
            "low_confidence_pages": low_confidence_pages,
        }
