"""Tests for OCR module with preprocessed images."""

import unittest
from unittest.mock import MagicMock, patch


class TestTesseractOCR(unittest.TestCase):
    """Test OCR module behavior with mocked Tesseract."""

    @patch("app.ingestion.ocr.pytesseract.image_to_data")
    @patch("app.ingestion.ocr.OCRPreprocessor")
    def test_ocr_returns_structured_result(self, mock_preprocessor_cls, mock_tesseract):
        from app.ingestion.ocr import TesseractOCR

        # Mock preprocessor
        mock_preprocessor = MagicMock()
        mock_preprocessor.pdf_page_to_image.return_value = MagicMock()
        mock_preprocessor.preprocess.return_value = MagicMock()
        mock_preprocessor_cls.return_value = mock_preprocessor

        # Mock Tesseract output
        mock_tesseract.return_value = {
            "text": ["Hello", "world", ""],
            "conf": [90, 85, -1],
        }

        ocr = TesseractOCR()
        page = MagicMock()
        page.number = 2  # Page 3 (0-indexed)
        result = ocr.ocr_page(page, cumulative_offset=50)

        assert result.page_number == 3
        assert "Hello" in result.text
        assert "world" in result.text
        assert result.source == "OCR"
        assert result.char_start == 50
        assert result.low_confidence_warning is False  # avg 87.5 > 70

    @patch("app.ingestion.ocr.pytesseract.image_to_data")
    @patch("app.ingestion.ocr.OCRPreprocessor")
    def test_low_confidence_sets_warning(self, mock_preprocessor_cls, mock_tesseract):
        from app.ingestion.ocr import TesseractOCR

        mock_preprocessor = MagicMock()
        mock_preprocessor.pdf_page_to_image.return_value = MagicMock()
        mock_preprocessor.preprocess.return_value = MagicMock()
        mock_preprocessor_cls.return_value = mock_preprocessor

        # Low confidence scores
        mock_tesseract.return_value = {
            "text": ["abc", "def"],
            "conf": [45, 55],
        }

        ocr = TesseractOCR()
        page = MagicMock()
        page.number = 0
        result = ocr.ocr_page(page)

        assert result.low_confidence_warning is True
        assert result.confidence < 70.0


if __name__ == "__main__":
    unittest.main()
