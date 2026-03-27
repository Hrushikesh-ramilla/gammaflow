"use client";

import { useEffect, useCallback, useRef } from "react";
import { useWebSocket } from "./useWebSocket";
import { WS_BASE } from "@/lib/constants";

export type ProcessingEvent =
  | { type: "page_processed"; page: number; total: number; source_type: string; confidence: number | null; warning?: string }
  | { type: "complete"; total_pages: number; chunk_count: number; warnings: string[] }
  | { type: "error"; message: string }
  | { type: "ping" };

interface UseProcessingStatusOptions {
  jobId: string | null;
  onPageProcessed?: (page: number, total: number, sourceType: string) => void;
  onComplete?: (totalPages: number, chunkCount: number) => void;
  onError?: (message: string) => void;
}

export function useProcessingStatus({
  jobId,
  onPageProcessed,
  onComplete,
  onError,
}: UseProcessingStatusOptions) {
  const url = jobId ? `${WS_BASE}/ws/processing/${jobId}` : "";

  const handleMessage = useCallback(
    (data: Record<string, unknown>) => {
      const event = data as ProcessingEvent;

      switch (event.type) {
        case "page_processed":
          onPageProcessed?.(event.page, event.total, event.source_type);
          break;
        case "complete":
          onComplete?.(event.total_pages, event.chunk_count);
          break;
        case "error":
          onError?.(event.message);
          break;
      }
    },
    [onPageProcessed, onComplete, onError]
  );

  return useWebSocket({
    url,
    onMessage: handleMessage,
    reconnectInterval: 2000,
    maxRetries: 3,
  });
}
