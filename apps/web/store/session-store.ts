"use client";

import { create } from "zustand";
import type { Message, Session, Citation, StreamEvent } from "@/lib/types";

interface SessionState {
  session: Session | null;
  messages: Message[];
  streamingContent: string;
  isStreaming: boolean;
  deviationDepth: number;
  currentCitations: Citation[];
  provider: string | null;
  error: string | null;

  // Actions
  setSession: (session: Session) => void;
  addMessage: (msg: Message) => void;
  appendToken: (token: string) => void;
  setStreaming: (isStreaming: boolean) => void;
  pushCitation: (citation: Citation) => void;
  clearStreamingState: () => void;
  setDeviationDepth: (depth: number) => void;
  setProvider: (provider: string) => void;
  setError: (error: string | null) => void;
  setMessages: (messages: Message[]) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  session: null,
  messages: [],
  streamingContent: "",
  isStreaming: false,
  deviationDepth: 0,
  currentCitations: [],
  provider: null,
  error: null,

  setSession: (session) => set({ session, deviationDepth: session.deviation_depth }),

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  appendToken: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),

  setStreaming: (isStreaming) => set({ isStreaming }),

  pushCitation: (citation) =>
    set((state) => ({
      currentCitations: [...state.currentCitations, citation],
    })),

  clearStreamingState: () =>
    set({ streamingContent: "", currentCitations: [], isStreaming: false }),

  setDeviationDepth: (depth) => set({ deviationDepth: depth }),

  setProvider: (provider) => set({ provider }),

  setError: (error) => set({ error }),

  setMessages: (messages) => set({ messages }),
}));
