"use client";

import React from "react";
import type { Message } from "@/lib/types";
import { CitationsList } from "./CitationChip";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const isUser = message.role === "user";

  const providerLabel =
    message.provider === "claude"
      ? "Claude"
      : message.provider === "openai"
      ? "GPT-4o"
      : message.provider === "fallback"
      ? "Fallback"
      : null;

  return (
    <div
      className={`message-bubble ${isUser ? "message-bubble--user" : "message-bubble--assistant"}`}
      data-role={message.role}
    >
      {/* Avatar */}
      <div className={`message-avatar ${isUser ? "message-avatar--user" : "message-avatar--assistant"}`}>
        {isUser ? "U" : "S"}
      </div>

      {/* Content */}
      <div className="message-content">
        <div className={`message-text ${isStreaming ? "message-text--streaming" : ""}`}>
          {message.content}
          {isStreaming && <span className="streaming-cursor" aria-hidden="true">▋</span>}
        </div>

        {/* Citations */}
        {!isStreaming && message.citations && message.citations.length > 0 && (
          <CitationsList citations={message.citations} />
        )}

        {/* Footer */}
        <div className="message-footer">
          <div className="message-footer-left">
            {providerLabel && (
              <span className="message-provider">via {providerLabel}</span>
            )}
            <span className="message-time">
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
          
          {!isUser && !isStreaming && (
            <button 
              className="citation-feedback-btn"
              onClick={() => console.log('Citation reported:', message.id)}
              aria-label="Report incorrect citation"
              title="Report incorrect citation"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path>
                <line x1="4" y1="22" x2="4" y2="15"></line>
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
