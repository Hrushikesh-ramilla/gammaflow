"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, Send, ChevronLeft, ChevronRight, Loader2, RotateCcw, FileWarning } from "lucide-react";

interface Citation {
  pageNumber: number;
  documentName: string;
  charStart?: number;
  charEnd?: number;
  sourceType?: "PDF" | "OCR";
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  provider?: string;
  isStreaming?: boolean;
}

interface ChatPanelProps {
  sessionId: string;
  topicName: string;
  onCitationClick: (citation: Citation) => void;
  deviationDepth: number;
  onResume: () => void;
}

export function ChatPanel({
  sessionId,
  topicName,
  onCitationClick,
  deviationDepth,
  onResume,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setStreamingContent("");

    // TODO: wire to actual WebSocket streaming endpoint
    // Simulate streaming for now
    setTimeout(() => {
      const mockResponse = `Based on your textbook, here's the explanation:

**Key Concept**: ${topicName} involves several fundamental principles that build on each other...

This is explained comprehensively [Page 47, Textbook] where the author defines it as a systematic approach to organizing information. The professor's notes [Page 12, Notes] provide additional context about how this appears in examinations.

Specifically, the algorithm works by:
1. Dividing the problem recursively [Page 48, Textbook]
2. Combining sub-solutions efficiently [Page 49, Textbook]
3. Achieving optimal time complexity [Page 51, Textbook]`;

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: mockResponse,
          citations: [
            { pageNumber: 47, documentName: "Textbook", sourceType: "PDF" },
            { pageNumber: 12, documentName: "Notes", sourceType: "OCR" },
          ],
          provider: "claude",
        },
      ]);
      setIsLoading(false);
    }, 1200);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const renderMessageContent = (message: Message) => {
    // Parse and render content with citation chips
    const parts = message.content.split(/(\[Page \d+[^\]]*\])/g);
    return (
      <div className="prose-syl">
        {parts.map((part, i) => {
          const citationMatch = part.match(/\[Page (\d+)(?:[,—–-]\s*([^\]]+))?\]/);
          if (citationMatch) {
            const pageNum = parseInt(citationMatch[1]);
            const docName = citationMatch[2] || "Document";
            const citation = message.citations?.find((c) => c.pageNumber === pageNum);
            return (
              <button
                key={i}
                className="citation-chip"
                onClick={() =>
                  onCitationClick({
                    pageNumber: pageNum,
                    documentName: docName,
                    sourceType: citation?.sourceType,
                  })
                }
                title={`Go to page ${pageNum}`}
              >
                {citation?.sourceType === "OCR" && <FileWarning className="w-3 h-3" />}
                p.{pageNum}
              </button>
            );
          }
          // Render bold text
          const rendered = part
            .split(/(\*\*[^*]+\*\*)/g)
            .map((seg, j) => {
              if (seg.startsWith("**") && seg.endsWith("**")) {
                return <strong key={j}>{seg.slice(2, -2)}</strong>;
              }
              return <span key={j}>{seg}</span>;
            });
          return <span key={i}>{rendered}</span>;
        })}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Topic header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 flex-shrink-0">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Studying</p>
          <h3 className="font-semibold text-white text-sm">{topicName}</h3>
        </div>
        <div className="flex items-center gap-2">
          {deviationDepth > 0 && (
            <button
              onClick={onResume}
              className="flex items-center gap-1 text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30 px-3 py-1 rounded-full hover:bg-amber-500/30 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Resume ({deviationDepth} levels)
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-16 h-16 rounded-2xl bg-indigo-500/20 flex items-center justify-center mb-4">
              <Brain className="w-8 h-8 text-indigo-400" />
            </div>
            <h3 className="font-semibold text-white mb-2">Ask about {topicName}</h3>
            <p className="text-gray-500 text-sm max-w-xs">
              I'll answer using exact quotes from your textbook and notes with page citations.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {message.role === "assistant" && (
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center mr-2 flex-shrink-0 mt-1">
                <Brain className="w-4 h-4 text-white" />
              </div>
            )}
            <div
              className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm ${
                message.role === "user"
                  ? "bg-indigo-600 text-white rounded-tr-sm"
                  : "glass text-gray-200 rounded-tl-sm"
              }`}
            >
              {message.role === "assistant" ? renderMessageContent(message) : message.content}
              {message.provider && message.provider !== "claude" && (
                <p className="text-xs text-gray-500 mt-2 pt-2 border-t border-white/5">
                  ⚡ Answered by {message.provider}
                </p>
              )}
            </div>
          </motion.div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 ml-9">
            <div className="glass px-4 py-3 rounded-2xl rounded-tl-sm">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/5 flex-shrink-0">
        <div className="flex items-end gap-3 glass rounded-2xl px-4 py-3">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask about ${topicName}…`}
            rows={1}
            className="flex-1 bg-transparent text-white placeholder-gray-500 text-sm resize-none focus:outline-none max-h-32"
            style={{ scrollbarWidth: "none" }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            id="send-message-btn"
            className="w-8 h-8 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg flex items-center justify-center transition-colors flex-shrink-0"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        <p className="text-[10px] text-gray-600 text-center mt-2">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  );
}
