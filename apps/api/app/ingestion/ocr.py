"""Tesseract OCR module with confidence scoring and per-page output."""

from dataclasses import dataclass

import pytesseract
import structlog
from PIL import Image

from app.config import settings
from app.ingestion.ocr_preprocessor import OCRPreprocessor

log = structlog.get_logger()


@dataclass
class OCRResult:
    """Result of OCR processing for a single page."""

    page_number: int  # 1-indexed
    text: str
    confidence: float  # 0.0 – 100.0 (Tesseract mean confidence)
    source: str = "OCR"
    char_start: int = 0
    char_end: int = 0
    low_confidence_warning: bool = False


class TesseractOCR:
    """OCR pipeline: preprocess → Tesseract → structured output."""

    TESSERACT_CONFIG = r"--oem 3 --psm 3 -l eng"

    def __init__(self):
        self.preprocessor = OCRPreprocessor()
        self.confidence_threshold = settings.OCR_CONFIDENCE_WARNING

    def ocr_page(self, page, cumulative_offset: int = 0) -> OCRResult:
        """Run OCR on a single PyMuPDF page.

        Args:
            page: fitz.Page object
            cumulative_offset: character offset for indexing

        Returns:
            OCRResult with text, confidence, and offset metadata
        """
        # Render page to image and preprocess
        raw_image = self.preprocessor.pdf_page_to_image(page, dpi=300)
        processed_image = self.preprocessor.preprocess(raw_image)

        # Run Tesseract with confidence data
        data = pytesseract.image_to_data(
            processed_image,
            config=self.TESSERACT_CONFIG,
            output_type=pytesseract.Output.DICT,
        )

        # Extract text and compute mean confidence (ignore -1 values)
        words = []
        confidences = []
        for i, word in enumerate(data["text"]):
            conf = data["conf"][i]
            if conf > 0 and word.strip():
                words.append(word)
                confidences.append(float(conf))

        text = " ".join(words)
        mean_confidence = float(sum(confidences) / len(confidences)) if confidences else 0.0

        low_conf = mean_confidence < self.confidence_threshold

        if low_conf:
            log.warning(
                "ocr.low_confidence",
                page=page.number + 1,
                confidence=round(mean_confidence, 1),
                threshold=self.confidence_threshold,
            )

        char_start = cumulative_offset
        char_end = cumulative_offset + len(text)

        log.debug(
            "ocr.page_processed",
            page=page.number + 1,
            chars=len(text),
            confidence=round(mean_confidence, 1),
        )

        return OCRResult(
            page_number=page.number + 1,
            text=text,
            confidence=mean_confidence,
            char_start=char_start,
            char_end=char_end,
            low_confidence_warning=low_conf,
        )
