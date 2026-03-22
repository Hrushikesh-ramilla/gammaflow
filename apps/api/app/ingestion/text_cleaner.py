"""OCR text cleaner — normalize OCR output for better embedding quality."""

import re
import unicodedata


class OCRTextCleaner:
    """Clean and normalize OCR-extracted text.

    OCR text often contains:
    - Zero-width characters and Unicode artifacts
    - Inconsistent spacing (double spaces, trailing spaces)
    - Common character substitution errors
    - Non-printable characters
    - Ligature or encoding artifacts
    """

    # Common OCR character substitution errors (pattern → correct)
    SUBSTITUTIONS = [
        (r"\brn\b", "m"),          # 'rn' mistaken for 'm' in many fonts
        (r"(?<=[a-z])0(?=[a-z])", "o"),  # digit 0 inside words → letter o
        (r"(?<=[a-z])1(?=[a-z])", "l"),  # digit 1 inside words → letter l
        (r"(?<=[A-Z])0(?=[A-Z])", "O"),  # digit 0 between caps → O
        (r"\|", "I"),               # pipe → capital I (common in headers)
        (r"—-|--", "—"),           # normalize dashes
    ]

    def clean(self, text: str) -> str:
        """Apply full cleaning pipeline to OCR text."""
        text = self._remove_unicode_artifacts(text)
        text = self._normalize_whitespace(text)
        text = self._fix_common_errors(text)
        text = self._remove_non_printable(text)
        return text.strip()

    def _remove_unicode_artifacts(self, text: str) -> str:
        """Remove zero-width chars, BOM, and normalize unicode."""
        # Remove zero-width characters
        text = text.replace("\ufeff", "")  # BOM
        text = text.replace("\u200b", "")  # zero-width space
        text = text.replace("\u200c", "")  # zero-width non-joiner
        text = text.replace("\u200d", "")  # zero-width joiner
        text = text.replace("\u00ad", "")  # soft hyphen
        # Normalize to NFC form
        text = unicodedata.normalize("NFC", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize multiple spaces, tabs, and excessive newlines."""
        # Replace tabs with spaces
        text = text.replace("\t", " ")
        # Collapse multiple spaces into one
        text = re.sub(r" {2,}", " ", text)
        # Collapse more than 2 consecutive newlines into 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove spaces at end of lines
        text = re.sub(r" +\n", "\n", text)
        return text

    def _fix_common_errors(self, text: str) -> str:
        """Fix known OCR substitution patterns."""
        for pattern, replacement in self.SUBSTITUTIONS:
            text = re.sub(pattern, replacement, text)
        return text

    def _remove_non_printable(self, text: str) -> str:
        """Remove characters that are not printable (control chars, etc.)."""
        return "".join(
            ch for ch in text
            if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t", " ")
        )
