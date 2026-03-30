"use client";

import { create } from "zustand";
import type { Citation } from "@/lib/types";

interface PDFState {
  // Current document
  documentId: string | null;
  documentUrl: string | null;
  currentPage: number;
  totalPages: number;
  scale: number;

  // Citation highlight
  activeCitation: Citation | null;
  highlightRect: DOMRect | null;

  // Sidebar open state
  isOpen: boolean;

  // Actions
  setDocument: (id: string, url: string) => void;
  setPage: (page: number) => void;
  setTotalPages: (total: number) => void;
  setScale: (scale: number) => void;
  jumpToPage: (page: number, citation?: Citation) => void;
  clearCitation: () => void;
  toggleSidebar: () => void;
  setOpen: (open: boolean) => void;
}

export const usePDFStore = create<PDFState>((set) => ({
  documentId: null,
  documentUrl: null,
  currentPage: 1,
  totalPages: 0,
  scale: 1.0,
  activeCitation: null,
  highlightRect: null,
  isOpen: false,

  setDocument: (id, url) =>
    set({ documentId: id, documentUrl: url, currentPage: 1 }),

  setPage: (page) => set({ currentPage: page }),

  setTotalPages: (total) => set({ totalPages: total }),

  setScale: (scale) => set({ scale: Math.max(0.5, Math.min(scale, 3.0)) }),

  jumpToPage: (page, citation) =>
    set({
      currentPage: page,
      activeCitation: citation ?? null,
    }),

  clearCitation: () => set({ activeCitation: null, highlightRect: null }),

  toggleSidebar: () => set((state) => ({ isOpen: !state.isOpen })),

  setOpen: (isOpen) => set({ isOpen }),
}));
