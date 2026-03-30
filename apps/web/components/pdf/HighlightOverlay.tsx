"use client";

import React, { useEffect, useState } from "react";
import { usePDFStore } from "@/store/pdf-store";
import type { Citation } from "@/lib/types";

export function HighlightOverlay() {
  const { activeCitation, currentPage, scale } = usePDFStore();
  const [highlightRect, setHighlightRect] = useState<DOMRect | null>(null);

  // This is a simplified approximation because rendering exact PDF text coordinates
  // natively in the browser requires integrating tightly with pdf.js.
  // For the purpose of the study engine's MVP frontend, we show a full-page
  // active state or a pseudo-highlight based on available citation data if any.

  useEffect(() => {
    if (!activeCitation) {
      setHighlightRect(null);
      return;
    }

    if (activeCitation.page !== currentPage) {
      setHighlightRect(null);
      return;
    }

    // In a full pdf.js implementation, we would map `char_start` to text-layer bounds.
    // Given we might not have exact coordinates yet from OCR, we create a generic
    // visual indicator on the page.
    setHighlightRect({
      x: 20 * scale,
      y: 100 * scale,
      width: 200 * scale,
      height: 30 * scale,
      top: 100 * scale,
      left: 20 * scale,
      bottom: 130 * scale,
      right: 220 * scale,
      toJSON: () => {}
    } as DOMRect);

    // Optional: timeout to fade out the highlight
    const timer = setTimeout(() => {
      // fade out
    }, 5000);

    return () => clearTimeout(timer);
  }, [activeCitation, currentPage, scale]);

  if (!activeCitation || activeCitation.page !== currentPage) {
    return null;
  }

  return (
    <div className="pdf-highlight-overlay" style={{ pointerEvents: "none" }}>
      {/* If we have an exact rect, ideally we'd position it absolute. */}
      <div 
        className="citation-highlight-pulse"
        style={{
          position: "absolute",
          top: highlightRect?.y ? highlightRect.y : "50%",
          left: highlightRect?.x ? highlightRect.x : "50%",
          width: highlightRect?.width ? highlightRect.width : "60%",
          height: highlightRect?.height ? highlightRect.height : "10%",
          transform: highlightRect ? "none" : "translate(-50%, -50%)",
          backgroundColor: activeCitation.source === "OCR" ? "rgba(255, 165, 0, 0.4)" : "rgba(255, 255, 0, 0.4)",
          boxShadow: "0 0 10px rgba(255, 255, 0, 0.8)",
          borderRadius: "4px",
          transition: "all 0.3s ease"
        }}
      />
    </div>
  );
}
