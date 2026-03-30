"use client";

import React, { useEffect, useRef, useState } from "react";
import { HighlightOverlay } from "./HighlightOverlay";

interface PdfPageProps {
  pageNumber: number;
  scale?: number;
  width?: number;
  // This is a stub for PDF.js implementation
  renderTextLayer?: boolean;
}

export function PdfPage({ pageNumber, scale = 1.0, width = 800, renderTextLayer = true }: PdfPageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  // Intersection Observer for Lazy Loading (Commit 202)
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "100% 0px" } // Load when within 1 viewport height
    );

    const currentRef = containerRef.current;
    if (currentRef) observer.observe(currentRef);

    return () => {
      if (currentRef) observer.unobserve(currentRef);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`pdf-page pdf-page--${isVisible ? 'loaded' : 'unloaded'}`}
      data-page-number={pageNumber}
      style={{
        width: width * scale,
        height: (width * 1.414) * scale, // A4 aspect approx
        position: "relative",
      }}
      aria-label={`PDF Page ${pageNumber}`}
    >
      {isVisible ? (
        <>
          <div className="pdf-page__canvas-mock">
            {/* Native pdf.js Canvas would render here */}
            <span className="pdf-page__watermark">Page {pageNumber}</span>
          </div>
          {renderTextLayer && <HighlightOverlay />}
        </>
      ) : (
        <div className="pdf-page__skeleton" aria-hidden="true" />
      )}
    </div>
  );
}
