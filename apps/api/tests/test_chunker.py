"""Tests for adaptive text chunker."""

import unittest

from app.ingestion.chunker import AdaptiveChunker


class TestAdaptiveChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = AdaptiveChunker()

    def test_pdf_page_produces_chunks(self):
        text = "Hello world. " * 200  # ~2600 chars — should produce multiple chunks
        chunks = self.chunker.chunk_page(
            text=text,
            page_number=1,
            source_type="PDF",
            ocr_confidence=1.0,
        )
        assert len(chunks) > 1
        for c in chunks:
            assert c.source_type == "PDF"
            assert c.page_number == 1

    def test_ocr_page_produces_smaller_chunks(self):
        text = "Noisy text. " * 200
        ocr_chunks = self.chunker.chunk_page(
            text=text, page_number=2, source_type="OCR", ocr_confidence=75.0
        )
        pdf_chunks = self.chunker.chunk_page(
            text=text, page_number=3, source_type="PDF"
        )
        # OCR chunks should be smaller → more of them
        avg_ocr_len = sum(len(c.text) for c in ocr_chunks) / max(len(ocr_chunks), 1)
        avg_pdf_len = sum(len(c.text) for c in pdf_chunks) / max(len(pdf_chunks), 1)
        assert avg_ocr_len <= avg_pdf_len

    def test_empty_text_returns_no_chunks(self):
        chunks = self.chunker.chunk_page(
            text="   ", page_number=1, source_type="PDF"
        )
        assert chunks == []

    def test_chunk_index_is_sequential(self):
        text = "A sentence here. " * 300
        chunks = self.chunker.chunk_page(
            text=text, page_number=1, source_type="PDF", chunk_index_start=0
        )
        for i, c in enumerate(chunks):
            assert c.chunk_index == i

    def test_chunk_carries_ocr_confidence(self):
        text = "Some scanned text. " * 100
        chunks = self.chunker.chunk_page(
            text=text, page_number=5, source_type="OCR", ocr_confidence=62.5
        )
        for c in chunks:
            assert c.ocr_confidence == 62.5

    def test_char_offsets_non_negative(self):
        text = "Test text. " * 150
        chunks = self.chunker.chunk_page(
            text=text, page_number=1, source_type="PDF", char_base_offset=1000
        )
        for c in chunks:
            assert c.char_start >= 1000
            assert c.char_end > c.char_start


if __name__ == "__main__":
    unittest.main()
