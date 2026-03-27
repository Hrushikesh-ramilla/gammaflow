/**
 * Shared TypeScript types used across the SYL frontend.
 * These mirror the Pydantic models on the FastAPI backend.
 */

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
}

// ---------------------------------------------------------------------------
// Documents & Ingestion
// ---------------------------------------------------------------------------

export type DocumentRole = "SYLLABUS" | "TEXTBOOK" | "NOTES";
export type ProcessingStatus = "queued" | "processing" | "completed" | "failed";

export interface Document {
  id: string;
  filename: string;
  role: DocumentRole;
  processing_status: ProcessingStatus;
  total_pages: number | null;
  chunk_count: number | null;
  created_at: string;
}

export interface ProcessingStatusResponse {
  document_id: string;
  status: ProcessingStatus;
  pages_done: number;
  total_pages: number;
  warnings: string[];
  error: string | null;
}

// ---------------------------------------------------------------------------
// Syllabuses & Topics
// ---------------------------------------------------------------------------

export interface Syllabus {
  id: string;
  course_name: string;
  user_id: string;
  document_id: string | null;
  topic_count: number;
  created_at: string;
}

export interface Topic {
  id: string;
  name: string;
  description: string;
  estimated_depth: "introductory" | "intermediate" | "advanced";
  prerequisites: string[];
  week_number: number | null;
}

export interface GraphNodeData {
  label: string;
  description: string;
  depth: "introductory" | "intermediate" | "advanced";
  status: "not_started" | "in_progress" | "completed";
  prerequisites: string[];
  isActive?: boolean;
  isCompleted?: boolean;
  onClick?: () => void;
}

export interface KnowledgeGraphData {
  syllabus_id: string;
  course_name: string;
  nodes: import("reactflow").Node<GraphNodeData>[];
  edges: import("reactflow").Edge[];
  topic_count: number;
}

// ---------------------------------------------------------------------------
// Sessions & Chat
// ---------------------------------------------------------------------------

export interface Session {
  id: string;
  syllabus_id: string;
  topic_id: string | null;
  topic_name: string | null;
  deviation_depth: number;
  message_count: number;
  created_at: string;
}

export interface Citation {
  page: number;
  doc: string;
  source: "PDF" | "OCR";
  char_start?: number | null;
  char_end?: number | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  provider?: "claude" | "openai" | "fallback";
  created_at: string;
}

// SSE Event types from the streaming endpoint
export type StreamEvent =
  | { type: "token"; content: string; provider: string }
  | { type: "citation"; page: number; doc: string; source: string; char_start?: number; char_end?: number }
  | { type: "provider_switched"; from: string; to: string; reason: string }
  | { type: "deviation"; depth: number; topic: string }
  | { type: "complete"; provider: string; tokens_used: number; message_id: string; cached?: boolean }
  | { type: "error"; message: string }
  | { type: "ping" };

// ---------------------------------------------------------------------------
// Problems
// ---------------------------------------------------------------------------

export type ProblemTier = "EXAM_LIKELY" | "GOOD_PRACTICE" | "OPTIONAL";
export type ProblemStatus = "todo" | "in_progress" | "done";

export interface Problem {
  id: string;
  document_id: string;
  problem_number: string | null;
  problem_text: string;
  page_number: number;
  chapter: string | null;
  rank_tier: ProblemTier | null;
  similarity_score: number | null;
  user_status: ProblemStatus;
}

// ---------------------------------------------------------------------------
// Note Mapping
// ---------------------------------------------------------------------------

export type MappingConfidence = "HIGH" | "MEDIUM" | "LOW";

export interface NoteMapping {
  note_chunk_id: string;
  note_page_number: number;
  textbook_chunk_id: string;
  textbook_page_number: number;
  similarity_score: number;
  confidence: MappingConfidence;
}

// ---------------------------------------------------------------------------
// Progress
// ---------------------------------------------------------------------------

export type TopicProgressStatus = "not_started" | "in_progress" | "completed";

export interface TopicProgress {
  topic_id: string;
  topic_name: string;
  status: TopicProgressStatus;
  started_at?: string;
  completed_at?: string;
}
