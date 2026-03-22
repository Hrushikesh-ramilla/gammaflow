"""Adaptive text chunker with source-aware sizing.

Text-based pages: 400-600 tokens, 50-token overlap
OCR-based pages: 300-400 tokens, 80-token overlap (more overlap for noisy text)
"""

from dataclasses import dataclass, field
from typing import Optional

import structlog

from app.config import settings

log = structlog.get_logger()

# Approximate: 1 token ≈ 4 characters (for English text)
CHARS_PER_TOKEN = 4


@dataclass
class TextChunk:
    """A single chunk of text ready for embedding."""

    chunk_index: int
    text: str
    char_start: int
    char_end: int
    page_number: int
    source_type: str  # 'PDF' | 'OCR'
    ocr_confidence: float = 1.0
    token_estimate: int = 0


class AdaptiveChunker:
    """Chunks text with parameters adapted to source type (PDF vs OCR).

    Key design:
    - OCR text gets smaller chunks + more overlap because it's noisier
    - Sentence boundaries are respected — never split mid-sentence
    - Each chunk carries its page number and source type metadata
    """

    def __init__(self):
        # Text PDF settings
        self.text_chunk_tokens = settings.TEXT_CHUNK_SIZE      # 500
        self.text_overlap_tokens = settings.TEXT_CHUNK_OVERLAP  # 50

        # OCR settings — smaller, more overlap
        self.ocr_chunk_tokens = settings.OCR_CHUNK_SIZE        # 350
        self.ocr_overlap_tokens = settings.OCR_CHUNK_OVERLAP   # 80

    def chunk_page(
        self,
        text: str,
        page_number: int,
        source_type: str,
        ocr_confidence: float = 1.0,
        char_base_offset: int = 0,
        chunk_index_start: int = 0,
    ) -> list[TextChunk]:
        """Chunk a single page's text into overlapping segments.

        Args:
            text: The page text (cleaned)
            page_number: 1-indexed page number
            source_type: 'PDF' or 'OCR'
            ocr_confidence: Tesseract confidence (0-100), 1.0 for PDF
            char_base_offset: cumulative character offset in document
            chunk_index_start: starting chunk index for this document

        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            return []

        is_ocr = source_type == "OCR"
        target_tokens = self.ocr_chunk_tokens if is_ocr else self.text_chunk_tokens
        overlap_tokens = self.ocr_overlap_tokens if is_ocr else self.text_overlap_tokens

        target_chars = target_tokens * CHARS_PER_TOKEN
        overlap_chars = overlap_tokens * CHARS_PER_TOKEN

        sentences = self._split_sentences(text)
        chunks = []
        chunk_idx = chunk_index_start
        current_start = 0

        while current_start < len(sentences):
            chunk_sentences = []
            chunk_len = 0

            i = current_start
            while i < len(sentences):
                s_len = len(sentences[i])
                if chunk_len + s_len > target_chars and chunk_sentences:
                    break
                chunk_sentences.append(sentences[i])
                chunk_len += s_len
                i += 1

            if not chunk_sentences:
                # Single sentence exceeds target — take it anyway
                chunk_sentences = [sentences[current_start]]
                i = current_start + 1

            chunk_text = " ".join(chunk_sentences).strip()
            # Compute character offsets relative to the original page text
            local_start = text.find(chunk_sentences[0]) if chunk_sentences else 0
            local_end = local_start + len(chunk_text)

            chunks.append(
                TextChunk(
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    char_start=char_base_offset + local_start,
                    char_end=char_base_offset + local_end,
                    page_number=page_number,
                    source_type=source_type,
                    ocr_confidence=ocr_confidence,
                    token_estimate=len(chunk_text) // CHARS_PER_TOKEN,
                )
            )
            chunk_idx += 1

            # Advance with overlap — backtrack by overlap_chars worth of sentences
            overlap_len = 0
            overlap_back = 0
            j = i - 1
            while j >= current_start and overlap_len < overlap_chars:
                overlap_len += len(sentences[j])
                overlap_back += 1
                j -= 1

            current_start = max(current_start + 1, i - overlap_back)

        log.debug(
            "chunker.page_chunked",
            page=page_number,
            source=source_type,
            chunks=len(chunks),
        )
        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences, respecting common abbreviations."""
        import re
        # Simple sentence splitter — split on . ! ? followed by whitespace + capital
        # Keep the delimiter with the sentence
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        # Filter empty parts
        return [p.strip() for p in parts if p.strip()]
