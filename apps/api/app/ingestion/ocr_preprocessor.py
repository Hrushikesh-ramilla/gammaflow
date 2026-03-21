"""OCR image preprocessor — grayscale, threshold, denoise, deskew."""

import io
import math

import cv2
import numpy as np
from PIL import Image


class OCRPreprocessor:
    """Applies image preprocessing to maximize Tesseract OCR accuracy.

    Pipeline:
    1. Convert to grayscale
    2. Upscale to 300 DPI equivalent if smaller
    3. Adaptive thresholding (Otsu's method)
    4. Denoising (Non-local means)
    5. Deskew correction (Hough transform)
    """

    TARGET_DPI = 300
    MIN_LEN = 1800  # minimum pixel dimension for 300 DPI on A4

    def preprocess(self, image: Image.Image) -> Image.Image:
        """Run full preprocessing pipeline on a PIL image."""
        img = np.array(image)

        # 1. Grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img

        # 2. Upscale if too small
        h, w = gray.shape
        if min(h, w) < self.MIN_LEN:
            scale = self.MIN_LEN / min(h, w)
            gray = cv2.resize(
                gray,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_CUBIC,
            )

        # 3. Adaptive threshold (Otsu's)
        _, thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # 4. Denoise
        denoised = cv2.fastNlMeansDenoising(thresh, h=10)

        # 5. Deskew
        deskewed = self._deskew(denoised)

        return Image.fromarray(deskewed)

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """Correct skew using Hough transform."""
        try:
            coords = np.column_stack(np.where(img > 0))
            if len(coords) < 100:
                return img
            angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            if abs(angle) < 0.5:  # skip trivial corrections
                return img

            (h, w) = img.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                img, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return rotated
        except Exception:
            return img  # graceful fallback

    def pdf_page_to_image(self, page, dpi: int = 300) -> Image.Image:
        """Render a PyMuPDF page to a PIL Image at given DPI."""
        mat = page.get_pixmap(dpi=dpi)
        img_bytes = mat.tobytes("png")
        return Image.open(io.BytesIO(img_bytes))
