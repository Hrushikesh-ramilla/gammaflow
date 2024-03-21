"""PyMuPDF text extractor with page metadata preservation."""

from dataclasses import dataclass

import fitz  # PyMuPDF
import structlog

log = structlog.get_logger()


@dataclass
class ExtractedPage:
    """Text extracted from a single PDF page via PyMuPDF."""

    page_number: int  # 1-indexed
    text: str
    char_start: int  # character offset in document-level cumulative text
    char_end: int
    source: str = "PDF"
    confidence: float = 1.0  # PDF extraction is always 1.0


class PDFExtractor:
    """Extracts text from text-selectable PDF pages using PyMuPDF."""

    def extract_page(self, page: fitz.Page, cumulative_offset: int = 0) -> ExtractedPage:
        """Extract text from a single page with character offset tracking."""
        text = page.get_text("text")
        char_start = cumulative_offset
        char_end = cumulative_offset + len(text)
        return ExtractedPage(
            page_number=page.number + 1,
            text=text,
            char_start=char_start,
            char_end=char_end,
        )

    def extract_document(self, doc: fitz.Document) -> list[ExtractedPage]:
        """Extract text from all pages, tracking cumulative character offsets."""
        pages = []
        cumulative_offset = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            extracted = self.extract_page(page, cumulative_offset)
            pages.append(extracted)
            cumulative_offset = extracted.char_end
            log.debug(
                "extractor.page_extracted",
                page=extracted.page_number,
                chars=len(extracted.text),
            )
        return pages
