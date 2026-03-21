"""Tests for PDF extractor and per-page type detector."""

import unittest
from unittest.mock import MagicMock, patch

from app.ingestion.detector import PageDetector, PageType
from app.ingestion.extractor import PDFExtractor


class TestPageDetector(unittest.TestCase):
    def setUp(self):
        self.detector = PageDetector(text_threshold=50)

    def _make_page(self, text: str):
        page = MagicMock()
        page.get_text.return_value = text
        page.number = 0
        return page

    def test_text_page_classified_correctly(self):
        page = self._make_page("This is a fully text-selectable page with enough content to pass.")
        assert self.detector.classify_page(page) == PageType.TEXT

    def test_scanned_page_classified_correctly(self):
        page = self._make_page("   ")  # minimal text → scanned
        assert self.detector.classify_page(page) == PageType.SCANNED

    def test_borderline_page_classified_as_scanned(self):
        page = self._make_page("x" * 49)  # just below threshold
        assert self.detector.classify_page(page) == PageType.SCANNED

    def test_exactly_at_threshold_classified_as_text(self):
        page = self._make_page("x" * 50)
        assert self.detector.classify_page(page) == PageType.TEXT

    def test_classify_document_returns_per_page_results(self):
        doc = MagicMock()
        doc.__len__ = lambda self: 3
        pages = [
            self._make_page("Long text content that is clearly selectable and full of words"),
            self._make_page(""),        # scanned
            self._make_page("Another long page with plenty of text for the detector"),
        ]
        doc.__getitem__ = lambda self, i: pages[i]
        results = self.detector.classify_document(doc)
        assert len(results) == 3
        assert results[0]["page_type"] == PageType.TEXT
        assert results[1]["page_type"] == PageType.SCANNED
        assert results[2]["page_type"] == PageType.TEXT


class TestPDFExtractor(unittest.TestCase):
    def _make_page(self, text: str, page_num: int = 0):
        page = MagicMock()
        page.get_text.return_value = text
        page.number = page_num
        return page

    def test_extract_page_returns_correct_structure(self):
        extractor = PDFExtractor()
        page = self._make_page("Hello world.", page_num=0)
        result = extractor.extract_page(page, cumulative_offset=0)
        assert result.page_number == 1
        assert result.text == "Hello world."
        assert result.char_start == 0
        assert result.char_end == len("Hello world.")
        assert result.source == "PDF"
        assert result.confidence == 1.0

    def test_extract_page_tracks_cumulative_offset(self):
        extractor = PDFExtractor()
        page = self._make_page("Second page.", page_num=1)
        result = extractor.extract_page(page, cumulative_offset=100)
        assert result.char_start == 100
        assert result.char_end == 100 + len("Second page.")


if __name__ == "__main__":
    unittest.main()
