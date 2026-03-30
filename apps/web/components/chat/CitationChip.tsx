"use client";

import React from "react";
import type { Citation } from "@/lib/types";
import { usePDFStore } from "@/store/pdf-store";

interface CitationChipProps {
  citation: Citation;
  index: number;
  variant?: "inline" | "list";
}

export function CitationChip({ citation, index, variant = "inline" }: CitationChipProps) {
  const { jumpToPage } = usePDFStore();

  const handleClick = () => {
    jumpToPage(citation.page, citation);
  };

  const isOCR = citation.source === "OCR";
  const label = `p.${citation.page}${citation.doc !== "Document" ? ` · ${citation.doc}` : ""}`;

  if (variant === "list") {
    return (
      <button
        onClick={handleClick}
        className="citation-chip-list"
        title={`Jump to ${citation.doc}, page ${citation.page}${isOCR ? " (OCR scan)" : ""}`}
      >
        <span className="citation-index">[{index + 1}]</span>
        <span className="citation-page-label">{label}</span>
        {isOCR && <span className="citation-ocr-badge">OCR</span>}
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      className="citation-chip-inline"
      title={`${citation.doc} — Page ${citation.page}${isOCR ? " (scanned)" : ""}`}
    >
      [{index + 1}]
      {isOCR && <span className="citation-ocr-dot" aria-label="OCR page" />}
    </button>
  );
}

// Render all citations from a message as inline chips
export function CitationsList({ citations }: { citations: Citation[] }) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="citations-container">
      <span className="citations-label">Sources:</span>
      <div className="citations-chips">
        {citations.map((cit, i) => (
          <CitationChip key={`${cit.page}-${cit.doc}-${i}`} citation={cit} index={i} variant="list" />
        ))}
      </div>
    </div>
  );
}
