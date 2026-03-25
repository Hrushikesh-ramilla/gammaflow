"""Citation parser — extracts [Page X, DocName] from LLM responses."""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class Citation:
    page_number: int
    document_name: str
    raw_text: str  # The original [Page X, Name] string


CITATION_PATTERN = re.compile(
    r"\[Page\s+(\d+)(?:\s*[,—–-]\s*([^\]]+))?\]",
    re.IGNORECASE,
)


def parse_citations(text: str) -> List[Citation]:
    """Extract all citations from an LLM response.

    Handles formats:
    - [Page 47, Textbook]
    - [Page 12 — Notes]
    - [Page 3]
    """
    citations = []
    for match in CITATION_PATTERN.finditer(text):
        page_str = match.group(1)
        doc_name = (match.group(2) or "Document").strip()
        try:
            page_num = int(page_str)
            citations.append(
                Citation(
                    page_number=page_num,
                    document_name=doc_name,
                    raw_text=match.group(0),
                )
            )
        except ValueError:
            continue
    return citations


def has_citations(text: str) -> bool:
    """Check if response contains at least one citation."""
    return bool(CITATION_PATTERN.search(text))
