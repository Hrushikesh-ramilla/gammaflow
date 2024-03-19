# SYL — Architecture Documentation

## System Overview

SYL is a syllabus-aware AI study engine built on a polyglot microservices architecture. Three backend services coordinate to deliver a seamless study experience.

```
┌─────────────────────────────────────────────────────────┐
│                    Browser Client                        │
│   Next.js 14 — Three panel layout                       │
│   React Flow — Knowledge graph                          │
│   PDF.js — Document viewer with highlight overlay       │
│   Framer Motion — State transition animations           │
└──────────────┬──────────────────────────────────────────┘
               │ HTTPS + WebSocket
┌──────────────▼──────────────────────────────────────────┐
│              Next.js API Routes (Gateway/BFF)            │
│   Authentication, rate limiting, request routing        │
└──────┬──────────────────┬───────────────────────────────┘
       │                  │
┌──────▼──────┐    ┌──────▼──────────────────────────────┐
│  Go Session  │    │     Python ML Pipeline               │
│  Orchestrator│    │     FastAPI                          │
│  :8080      │    │     :8000                            │
│             │    │                                      │
│  Session    │    │  Hybrid PDF pipeline:                │
│  state      │    │  - Per-page type detection           │
│  management │    │  - PyMuPDF text extraction           │
│             │    │  - OCR preprocessing + Tesseract     │
│  Deviation  │    │  - OCR text cleaning                 │
│  detection  │    │  - Adaptive chunking                 │
│             │    │  - sentence-transformers embedding   │
│  Progress   │    │  - Qdrant storage                    │
│  tracking   │    │                                      │
│             │    │  LLM Fallback Chain:                 │
│  LLM intent │    │  Claude → OpenAI → raw chunks        │
│  classify   │    │                                      │
└──────┬──────┘    └──────────────┬───────────────────────┘
       │                          │
┌──────▼──────┐    ┌──────────────▼───────────────────────┐
│  PostgreSQL  │    │         Qdrant                       │
│  :5432      │    │         :6333                        │
└──────┬──────┘    └──────────────────────────────────────┘
       │
┌──────▼──────┐
│    Redis     │
│    :6379    │
│  Response   │
│  cache      │
└─────────────┘
```

## Critical Design Decisions

### 1. Hybrid Per-Page PDF Detection

Real student documents are hybrid — some pages text-selectable, some scanned. SYL classifies every page individually:

```
For each page:
  text = extract_text(page)
  if len(text.strip()) < 50 chars:
    → OCR pipeline (preprocess → Tesseract → clean → adaptive chunks)
  else:
    → Direct extraction (PyMuPDF → standard chunks)
```

This is the most critical architectural decision. Global document classification fails for real-world Indian textbooks and WhatsApp-shared notes.

### 2. LLM Fallback Chain

```
User question
    ↓ Cache hit? → return cached
    ↓ miss
Try Claude Sonnet (primary)
    ↓ fail / timeout >5s / empty citations
Try OpenAI GPT-4o-mini
    ↓ fail
Return raw chunks + disclaimer
```

Smart triggers go beyond crashes: latency spikes, rate limits, empty citation responses.

### 3. Adaptive Highlighting

Citation highlighting adapts to page source type:
- **Text PDF**: character offset → precise paragraph highlight (amber #FCD34D, 40% opacity)
- **OCR/Scanned PDF**: full page amber border + "📄 Scanned document" indicator

### 4. Session Architecture (Go)

The Go orchestrator owns session state. Every message flow:
1. Load session from Postgres
2. Classify intent (Claude Haiku/OpenAI mini)
3. Push/pop deviation stack
4. Forward to FastAPI for retrieval + LLM
5. Stream tokens via WebSocket to browser
6. Persist updated state before streaming starts

### 5. Token Budget

Every LLM call is hard-capped at 6,000 tokens:
- System prompt: ~400 tokens
- Session summary: ~300 tokens
- Last 5 messages: ~800 tokens
- Retrieved chunks (top 5): ~2,000 tokens
- Current message: ~100 tokens
= ~3,600 tokens (headroom for response)

## Data Flow — Message Processing

```
Student sends message
        ↓
Next.js API Gateway (auth, rate limit)
        ↓
Go Orchestrator loads session state
        ↓
Classify intent → ON_TOPIC | DEVIATION | RESUME | NAVIGATION
        ↓
If DEVIATION: push to deviation_stack
If RESUME: pop deviation_stack, inject resume context
        ↓
Check response cache (Redis)
        ↓ miss
FastAPI: embed query → Qdrant search (topic-filtered)
        ↓
Build prompt (token-budgeted)
        ↓
Try Claude Sonnet → stream tokens
        ↓
Parse citations → emit to frontend for PDF scroll
        ↓
Persist session state, update progress
```

## Services

| Service | Port | Technology | Responsibility |
|---------|------|------------|---------------|
| web | 3000 | Next.js 14 | UI, routing, BFF |
| api | 8000 | FastAPI | ML pipeline, RAG, LLM |
| orchestrator | 8080 | Go | Session state, WebSocket, intent |
| postgres | 5432 | PostgreSQL 16 | Relational data |
| qdrant | 6333 | Qdrant | Vector search |
| redis | 6379 | Redis 7 | Response cache |
