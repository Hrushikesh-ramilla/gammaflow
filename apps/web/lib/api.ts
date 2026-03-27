/**
 * Typed API client for all SYL backend endpoints.
 *
 * Uses fetch with automatic JWT injection, error handling,
 * and typed response parsing.
 */

import type {
  Document,
  KnowledgeGraphData,
  Message,
  NoteMapping,
  Problem,
  ProblemStatus,
  ProblemTier,
  ProcessingStatusResponse,
  Session,
  Syllabus,
  TokenResponse,
  Topic,
  User,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else {
    // Try to get token from localStorage in browser
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("syl_token");
      if (stored) headers["Authorization"] = `Bearer ${stored}`;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? body.error ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const auth = {
  register: (email: string, password: string, full_name = "") =>
    apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: (email: string, password: string) =>
    apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => apiFetch<User>("/auth/me"),
};

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export const documents = {
  upload: (file: File, role: string, syllabus_id?: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("role", role);
    if (syllabus_id) form.append("syllabus_id", syllabus_id);

    const token =
      typeof window !== "undefined" ? localStorage.getItem("syl_token") : null;

    return fetch(`${API_BASE}/documents`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    }).then(async (res) => {
      if (!res.ok) throw new ApiError(res.status, await res.text());
      return res.json() as Promise<{ document_id: string; job_id: string; status: string }>;
    });
  },

  get: (id: string) => apiFetch<Document>(`/documents/${id}`),

  getStatus: (id: string) =>
    apiFetch<ProcessingStatusResponse>(`/documents/${id}/status`),
};

// ---------------------------------------------------------------------------
// Syllabuses
// ---------------------------------------------------------------------------

export const syllabuses = {
  list: () => apiFetch<Syllabus[]>("/syllabuses"),

  create: (course_name: string, document_id: string) =>
    apiFetch<Syllabus>("/syllabuses", {
      method: "POST",
      body: JSON.stringify({ course_name, document_id }),
    }),

  get: (id: string) => apiFetch<Syllabus>(`/syllabuses/${id}`),

  getGraph: (id: string) =>
    apiFetch<KnowledgeGraphData>(`/syllabuses/${id}/graph`),

  getTopics: (id: string) => apiFetch<Topic[]>(`/syllabuses/${id}/topics`),
};

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export const sessions = {
  create: (syllabus_id: string, topic_id?: string, topic_name?: string) =>
    apiFetch<Session>("/sessions", {
      method: "POST",
      body: JSON.stringify({ syllabus_id, topic_id, topic_name }),
    }),

  get: (id: string) => apiFetch<Session>(`/sessions/${id}`),

  getHistory: (id: string, limit = 50) =>
    apiFetch<Message[]>(`/sessions/${id}/history?limit=${limit}`),

  /**
   * Returns the raw Response for streaming SSE. Callers should
   * iterate over the body using a ReadableStream reader.
   */
  sendMessage: (
    sessionId: string,
    content: string,
    topic_id?: string,
    topic_name?: string
  ): Promise<Response> => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("syl_token") : null;
    return fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content, topic_id, topic_name }),
    });
  },
};

// ---------------------------------------------------------------------------
// Problems
// ---------------------------------------------------------------------------

export const problems = {
  list: (syllabusId: string, tier?: ProblemTier) => {
    const qs = tier ? `?tier=${tier}` : "";
    return apiFetch<Problem[]>(`/syllabuses/${syllabusId}/problems${qs}`);
  },

  extract: (document_id: string, syllabus_id: string, chapter?: string) =>
    apiFetch<{ status: string; document_id: string }>("/problems/extract", {
      method: "POST",
      body: JSON.stringify({ document_id, syllabus_id, chapter }),
    }),

  updateProgress: (problem_id: string, status: ProblemStatus) =>
    apiFetch<{ problem_id: string; status: string }>(
      `/problems/${problem_id}/progress`,
      { method: "PATCH", body: JSON.stringify({ status }) }
    ),
};

// ---------------------------------------------------------------------------
// Retrieval
// ---------------------------------------------------------------------------

export const retrieval = {
  search: (
    query: string,
    syllabus_id: string,
    top_k = 10,
    use_reranking = true
  ) =>
    apiFetch<{ query: string; results: object[]; total: number }>(
      "/retrieval/search",
      {
        method: "POST",
        body: JSON.stringify({ query, syllabus_id, top_k, use_reranking }),
      }
    ),
};

// ---------------------------------------------------------------------------
// Mapping
// ---------------------------------------------------------------------------

export const mapping = {
  compute: (
    syllabus_id: string,
    note_document_id: string,
    textbook_document_id: string
  ) =>
    apiFetch<{ status: string; syllabus_id: string }>("/mapping/compute", {
      method: "POST",
      body: JSON.stringify({
        syllabus_id,
        note_document_id,
        textbook_document_id,
      }),
    }),

  get: (syllabusId: string) =>
    apiFetch<{ syllabus_id: string; mappings: NoteMapping[]; total: number }>(
      `/syllabuses/${syllabusId}/mappings`
    ),
};

export { ApiError };
