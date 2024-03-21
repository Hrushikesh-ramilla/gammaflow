"""Per-page PDF type detector — text vs scanned vs hybrid."""

from enum import Enum

import fitz  # PyMuPDF
import structlog

from app.config import settings

log = structlog.get_logger()


class PageType(str, Enum):
    TEXT = "PDF"
    SCANNED = "OCR"


class PageDetector:
    """Classifies each PDF page individually as text-based or scanned."""

    def __init__(self, text_threshold: int = None):
        self.threshold = text_threshold or settings.OCR_TEXT_THRESHOLD

    def classify_page(self, page: fitz.Page) -> PageType:
        """Return PageType.TEXT or PageType.SCANNED for a single page.

        A page is considered scanned (image-based) if extractable text
        is below the configured character threshold. This handles:
        - Pure text PDFs → all pages TEXT
        - Pure scanned PDFs → all pages SCANNED
        - Hybrid PDFs (most common IRL) → mixed per page
        """
        text = page.get_text("text")
        char_count = len(text.strip())

        if char_count < self.threshold:
            log.debug(
                "page_detector.scanned",
                page=page.number + 1,
                char_count=char_count,
                threshold=self.threshold,
            )
            return PageType.SCANNED

        log.debug(
            "page_detector.text",
            page=page.number + 1,
            char_count=char_count,
        )
        return PageType.TEXT

    def classify_document(self, doc: fitz.Document) -> list[dict]:
        """Classify all pages in a document. Returns list of page classifications.

        Returns:
            List of dicts: [{page_number, page_type, char_count}]
        """
        results = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            char_count = len(text.strip())
            page_type = self.classify_page(page)
            results.append(
                {
                    "page_number": page_num + 1,  # 1-indexed
                    "page_type": page_type,
                    "char_count": char_count,
                }
            )

        scanned_count = sum(1 for r in results if r["page_type"] == PageType.SCANNED)
        text_count = len(results) - scanned_count
        log.info(
            "page_detector.document_classified",
            total_pages=len(results),
            text_pages=text_count,
            scanned_pages=scanned_count,
        )
        return results
