/** Application-wide constants. */

export const APP_NAME = "SYL";
export const APP_TAGLINE = "Study smarter. Learn deeper.";

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8080";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export const AUTH_TOKEN_KEY = "syl_token";
export const AUTH_USER_KEY = "syl_user";

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------
export const MAX_FILE_SIZE_MB = 100;
export const ALLOWED_FILE_TYPES = ["application/pdf"] as const;

// ---------------------------------------------------------------------------
// Problem tiers
// ---------------------------------------------------------------------------
export const TIER_LABELS = {
  EXAM_LIKELY: "Exam Likely",
  GOOD_PRACTICE: "Good Practice",
  OPTIONAL: "Optional",
} as const;

export const TIER_COLORS = {
  EXAM_LIKELY: {
    bg: "#FF4D6D",
    text: "#fff",
    badge: "bg-red-500 text-white",
  },
  GOOD_PRACTICE: {
    bg: "#F77F00",
    text: "#fff",
    badge: "bg-orange-500 text-white",
  },
  OPTIONAL: {
    bg: "#4CC9F0",
    text: "#fff",
    badge: "bg-sky-400 text-white",
  },
} as const;

// ---------------------------------------------------------------------------
// Deviation stack
// ---------------------------------------------------------------------------
export const MAX_DEVIATION_DEPTH = 5;

// ---------------------------------------------------------------------------
// Graph
// ---------------------------------------------------------------------------
export const DEPTH_COLORS = {
  introductory: "#4fc3f7",
  intermediate: "#ab47bc",
  advanced: "#ef5350",
} as const;

export const STATUS_COLORS = {
  not_started: "#334155",
  in_progress: "#7c3aed",
  completed: "#10b981",
} as const;

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------
export const MAX_MESSAGE_LENGTH = 4000;
export const MESSAGES_PER_PAGE = 50;

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  dashboard: "/dashboard",
  onboarding: "/onboarding",
  study: (id: string) => `/study/${id}`,
} as const;

export const PUBLIC_ROUTES = [
  ROUTES.home,
  ROUTES.login,
  ROUTES.register,
];
