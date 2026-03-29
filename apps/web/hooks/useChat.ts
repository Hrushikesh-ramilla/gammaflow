"use client";

import { useCallback, useRef, useState } from "react";
import { sessions } from "@/lib/api";
import type { Citation, Message, StreamEvent } from "@/lib/types";
import { useSessionStore } from "@/store/session-store";
import { usePDFStore } from "@/store/pdf-store";

interface UseChatOptions {
  sessionId: string;
  onDeviationDetected?: (depth: number, topic: string) => void;
}

export function useChat({ sessionId, onDeviationDetected }: UseChatOptions) {
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const {
    addMessage,
    appendToken,
    setStreaming,
    pushCitation,
    clearStreamingState,
    setDeviationDepth,
    setProvider,
    setError,
    streamingContent,
    messages,
  } = useSessionStore();

  const { jumpToPage } = usePDFStore();

  const sendMessage = useCallback(
    async (content: string, topicId?: string, topicName?: string) => {
      if (isLoading || !content.trim()) return;

      // Cancel any previous stream
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      // Optimistically add user message
      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      addMessage(userMsg);
      clearStreamingState();
      setStreaming(true);
      setIsLoading(true);
      setError(null);

      try {
        const response = await sessions.sendMessage(
          sessionId,
          content,
          topicId,
          topicName
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) throw new Error("No response body");

        let buffer = "";
        const citations: Citation[] = [];
        let assembledText = "";
        let finalMessageId = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            let event: StreamEvent;
            try {
              event = JSON.parse(raw);
            } catch {
              continue;
            }

            switch (event.type) {
              case "token":
                appendToken(event.content);
                assembledText += event.content;
                setProvider(event.provider);
                break;

              case "citation": {
                const cit: Citation = {
                  page: event.page,
                  doc: event.doc,
                  source: event.source as "PDF" | "OCR",
                  char_start: event.char_start,
                  char_end: event.char_end,
                };
                citations.push(cit);
                pushCitation(cit);
                // Auto-scroll PDF to first citation
                if (citations.length === 1) {
                  jumpToPage(cit.page, cit);
                }
                break;
              }

              case "provider_switched":
                setProvider(event.to);
                break;

              case "deviation":
                setDeviationDepth(event.depth);
                onDeviationDetected?.(event.depth, event.topic);
                break;

              case "complete": {
                finalMessageId = event.message_id;
                // Add finalized assistant message
                const assistantMsg: Message = {
                  id: event.message_id ?? `assistant-${Date.now()}`,
                  role: "assistant",
                  content: assembledText,
                  citations,
                  provider: event.provider as Message["provider"],
                  created_at: new Date().toISOString(),
                };
                addMessage(assistantMsg);
                clearStreamingState();
                break;
              }

              case "error":
                setError(event.message);
                break;
            }
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setError(err.message ?? "Failed to send message");
        }
      } finally {
        setIsLoading(false);
        setStreaming(false);
      }
    },
    [sessionId, isLoading, addMessage, appendToken, setStreaming, pushCitation, clearStreamingState, setDeviationDepth, setProvider, setError, jumpToPage, onDeviationDetected]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
    setIsLoading(false);
  }, [setStreaming]);

  return {
    sendMessage,
    cancelStream,
    isLoading,
    streamingContent,
    messages,
  };
}
