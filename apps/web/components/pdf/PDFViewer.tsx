"use client";

import { useEffect, useRef, useState } from "react";
import { FileWarning, ZoomIn, ZoomOut, ChevronLeft, ChevronRight } from "lucide-react";

interface PDFViewerProps {
  fileUrl: string;
  targetPage?: number;
  highlightCharStart?: number;
  highlightCharEnd?: number;
  sourceType?: "PDF" | "OCR";
  onPageChange?: (page: number) => void;
}

export function PDFViewer({
  fileUrl,
  targetPage = 1,
  highlightCharStart,
  highlightCharEnd,
  sourceType = "PDF",
  onPageChange,
}: PDFViewerProps) {
  const [currentPage, setCurrentPage] = useState(targetPage);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.2);
  const [isOCRPage, setIsOCRPage] = useState(false);
  const [isHighlighting, setIsHighlighting] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const highlightTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // Navigate to target page when citation is clicked
  useEffect(() => {
    if (targetPage !== currentPage) {
      setCurrentPage(targetPage);
      onPageChange?.(targetPage);
    }
  }, [targetPage]);

  // Trigger highlight animation when charStart changes
  useEffect(() => {
    if (highlightCharStart !== undefined) {
      setIsHighlighting(true);
      clearTimeout(highlightTimeoutRef.current);
      highlightTimeoutRef.current = setTimeout(() => setIsHighlighting(false), 8000);
    }
  }, [highlightCharStart, highlightCharEnd]);

  // Detect if current page is OCR
  useEffect(() => {
    setIsOCRPage(sourceType === "OCR");
  }, [sourceType]);

  const prev = () => setCurrentPage((p) => Math.max(1, p - 1));
  const next = () => setCurrentPage((p) => Math.min(totalPages || p + 1, p + 1));

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={prev}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-lg hover:bg-white/5 disabled:opacity-40 transition-colors text-gray-400"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-gray-400 min-w-[80px] text-center">
            {currentPage} / {totalPages || "—"}
          </span>
          <button
            onClick={next}
            disabled={totalPages ? currentPage >= totalPages : false}
            className="p-1.5 rounded-lg hover:bg-white/5 disabled:opacity-40 transition-colors text-gray-400"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          {isOCRPage && (
            <div className="flex items-center gap-1 text-amber-400 text-xs">
              <FileWarning className="w-3 h-3" />
              <span>Scanned page</span>
            </div>
          )}
          <button
            onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}
            className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-500">{Math.round(scale * 100)}%</span>
          <button
            onClick={() => setScale((s) => Math.min(3, s + 0.2))}
            className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* PDF Content */}
      <div ref={containerRef} className="flex-1 overflow-auto relative">
        {/* OCR page-level highlight */}
        {isHighlighting && isOCRPage && (
          <div className="absolute inset-0 pointer-events-none z-10 border-4 border-amber-400/70 animate-pulse rounded" />
        )}

        {/* PDF iframe placeholder — in production use PDF.js */}
        <div className="flex items-center justify-center min-h-full p-8">
          <div
            className="bg-white shadow-2xl text-gray-900 relative"
            style={{
              width: `${595 * scale}px`,
              minHeight: `${842 * scale}px`,
              padding: `${40 * scale}px`,
              fontSize: `${12 * scale}px`,
              lineHeight: `${1.6 * scale}em`,
            }}
          >
            {/* Citation text highlight overlay (PDF pages only) */}
            {isHighlighting && !isOCRPage && (
              <div
                className="citation-highlight absolute"
                style={{
                  top: `${100 * scale}px`,
                  left: `${40 * scale}px`,
                  right: `${40 * scale}px`,
                  height: `${48 * scale}px`,
                  zIndex: 10,
                }}
              />
            )}

            <div className="text-gray-400 text-center mt-8">
              <p className="text-lg font-semibold text-gray-700">Page {currentPage}</p>
              <p className="text-sm mt-2 text-gray-500">
                PDF viewer — wire PDF.js to render actual document content
              </p>
              {isOCRPage && (
                <div className="mt-4 flex items-center justify-center gap-2 text-amber-600 text-sm">
                  <FileWarning className="w-4 h-4" />
                  <span>This page was processed via OCR (scanned)</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
