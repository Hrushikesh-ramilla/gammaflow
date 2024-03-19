# SYL — Syllabus-Aware AI Study Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![Go](https://img.shields.io/badge/Go-1.22-cyan)](https://golang.org)

> Upload your syllabus + textbook + professor notes → get an interactive knowledge graph → click any topic → AI explains it using your exact book with page citations → autoscrolls PDF to the cited paragraph → tracks where you deviate → resumes from exactly where you left off.

## What SYL Does

SYL transforms how students interact with academic material. Upload three things:

1. **Syllabus** — your professor's topic list
2. **Textbook** — the reference book (PDF, text or scanned)
3. **Professor Notes** — handwritten or typed (WhatsApp PDF, scanned, anything)

SYL gives you:

- **Interactive knowledge graph** — syllabus rendered as a clickable DAG
- **AI tutor grounded in YOUR documents** — every answer cites a specific page
- **PDF autoscroll** — click a citation → PDF jumps to that paragraph
- **Deviation tracking** — go on tangents freely, resume from exact position
- **Problem ranker** — problems ranked by exam likelihood based on note coverage
- **Note-to-textbook mapping** — professor notes linked to textbook sections

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), React Flow, PDF.js, Framer Motion |
| ML Pipeline | FastAPI, PyMuPDF, Tesseract OCR, sentence-transformers |
| Session Orchestrator | Go 1.22, Chi router, WebSocket |
| Vector DB | Qdrant |
| Relational DB | PostgreSQL |
| AI | Claude Sonnet (primary), OpenAI GPT-4o-mini (fallback) |
| Deployment | Vercel (web), Fly.io (api + orchestrator), Qdrant Cloud |

## Quick Start (Local Development)

```bash
# Prerequisites: Docker, Node.js 20+, Python 3.11+, Go 1.22+, pnpm

# 1. Clone
git clone https://github.com/Hrushikesh-ramilla/SYL.git
cd SYL

# 2. Environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start infrastructure
docker-compose up -d

# 4. Install dependencies
pnpm install

# 5. Start all services
./scripts/dev.sh
```

## Architecture

```
Browser (Next.js 14)
    ↕ WebSocket + HTTPS
Go Session Orchestrator  ←→  FastAPI ML Pipeline
    ↕                              ↕
PostgreSQL              Qdrant Vector DB
                              ↕
                        Claude API + OpenAI API
```

See [docs/architecture.md](docs/architecture.md) for full architecture documentation.

## Citation Accuracy

SYL is designed to never hallucinate. Every answer must cite a specific page from uploaded documents. The system returns raw retrieved chunks if the AI models are unavailable — it will never fabricate.

**Target:** >85% citation accuracy within ±1 page.

## Author

**Hrushikesh Ramilla**  
ABV-IIITM Gwalior  
[ramillahrushikesh@gmail.com](mailto:ramillahrushikesh@gmail.com)

## License

MIT — see [LICENSE](LICENSE)
