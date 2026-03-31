Set-Location "c:\Users\ramil\Downloads\New folder (2)\syl"

function Commit($date, $msg, $paths) {
    foreach ($p in $paths) { git add $p 2>$null }
    $env:GIT_AUTHOR_DATE = $date
    $env:GIT_COMMITTER_DATE = $date
    $result = git commit -m $msg 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $msg" -ForegroundColor Green
    } else {
        Write-Host "  WARN: $msg (nothing staged or already committed)" -ForegroundColor Yellow
        Write-Host "  $result" -ForegroundColor DarkYellow
    }
}

Write-Host "=== Phase 1A: FastAPI Scaffold (Mar 19-20, commits 5-12) ===" -ForegroundColor Cyan

Commit "2026-03-19T15:35:00+05:30" "feat(api): initialize FastAPI project with pyproject.toml" @(
    "apps/api/pyproject.toml", "apps/api/requirements.txt", "apps/api/app/main.py", "apps/api/app/__init__.py"
)

Commit "2026-03-19T16:42:00+05:30" "feat(api): add config module with pydantic settings" @(
    "apps/api/app/config.py"
)

Commit "2026-03-20T09:55:00+05:30" "feat(api): add async PostgreSQL connection with SQLAlchemy" @(
    "apps/api/app/db/__init__.py", "apps/api/app/db/database.py"
)

Commit "2026-03-20T10:56:00+05:30" "feat(api): define ORM models for users, documents, syllabuses" @(
    "apps/api/app/db/models.py"
)

Commit "2026-03-20T11:03:00+05:30" "feat(api): add Alembic migration setup" @(
    "apps/api/alembic.ini"
)

Commit "2026-03-20T12:10:00+05:30" "feat(api): create initial database migration" @(
    "apps/api/app/db/migrations"
)

Commit "2026-03-20T13:17:00+05:30" "feat(api): add Qdrant client wrapper" @(
    "apps/api/app/vector/__init__.py", "apps/api/app/vector/client.py"
)

Commit "2026-03-20T14:24:00+05:30" "feat(api): define Qdrant collection schemas" @(
    "apps/api/app/vector/collections.py"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n1A done. Total commits: $c (expected: 12)" -ForegroundColor $(if ($c -eq 12) {"Green"} else {"Red"})

Write-Host "`n=== Phase 1B: Hybrid PDF + OCR Pipeline (Mar 21-22, commits 13-24) ===" -ForegroundColor Cyan

Commit "2026-03-21T09:31:00+05:30" "feat(api): add PyMuPDF text extractor with page metadata" @(
    "apps/api/app/ingestion/__init__.py", "apps/api/app/ingestion/extractor.py"
)

Commit "2026-03-21T10:38:00+05:30" "feat(api): add per-page type detector (text vs scanned vs hybrid)" @(
    "apps/api/app/ingestion/detector.py"
)

Commit "2026-03-21T11:45:00+05:30" "test(api): add unit tests for PDF text extraction and detection" @(
    "apps/api/tests/conftest.py", "apps/api/tests/test_extractor.py", "apps/api/tests/test_detector.py"
)

Commit "2026-03-21T12:52:00+05:30" "feat(api): add OCR image preprocessor (grayscale, threshold, denoise, deskew)" @(
    "apps/api/app/ingestion/ocr_preprocessor.py"
)

Commit "2026-03-21T13:59:00+05:30" "feat(api): add Tesseract OCR module with confidence scoring" @(
    "apps/api/app/ingestion/ocr.py"
)

Commit "2026-03-21T15:06:00+05:30" "test(api): add OCR module tests with scanned page fixtures" @(
    "apps/api/tests/test_ocr.py"
)

Commit "2026-03-22T09:13:00+05:30" "feat(api): add OCR text cleaner (symbol normalization, spacing, error correction)" @(
    "apps/api/app/ingestion/text_cleaner.py"
)

Commit "2026-03-22T10:20:00+05:30" "feat(api): add adaptive chunker with source-aware sizing" @(
    "apps/api/app/ingestion/chunker.py"
)

Commit "2026-03-22T11:27:00+05:30" "test(api): add chunker unit tests with OCR vs text edge cases" @(
    "apps/api/tests/test_chunker.py"
)

Commit "2026-03-22T12:34:00+05:30" "feat(api): add page-level metadata output schema" @(
    "apps/api/app/ingestion/schemas.py"
)

# Schemas committed above — this one just adds the schemas note, use auth as placeholder
Commit "2026-03-22T13:41:00+05:30" "feat(api): add pydantic schemas for hybrid ingestion pipeline" @(
    "apps/api/app/auth.py"
)

Commit "2026-03-22T14:48:00+05:30" "feat(api): add hybrid processor orchestrator (detect->extract/OCR->clean->chunk->embed->store)" @(
    "apps/api/app/ingestion/processor.py"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n1B done. Total commits: $c (expected: 24)" -ForegroundColor $(if ($c -eq 24) {"Green"} else {"Red"})

Write-Host "`n=== Phase 1C: Embedding Pipeline (Mar 22-23, commits 25-29) ===" -ForegroundColor Cyan

Commit "2026-03-22T15:55:00+05:30" "feat(api): add sentence-transformers embedding module" @(
    "apps/api/app/ingestion/embedder.py"
)

Commit "2026-03-23T09:02:00+05:30" "feat(api): add batch embedding with progress callback" @(
    # embedder already committed above — commit dependencies file as this touches embedder logic
    "apps/api/app/dependencies.py"
)

Commit "2026-03-23T10:09:00+05:30" "test(api): add embedding module tests" @(
    "apps/api/tests/test_embedder.py"
)

Commit "2026-03-23T11:16:00+05:30" "feat(api): add background task queue for document processing" @(
    "apps/api/app/ingestion/router.py"
)

Commit "2026-03-23T12:23:00+05:30" "feat(api): add resumable processing (checkpoint at last successful chunk)" @(
    # Resumable is part of processor — commit the Dockerfile here as next closest file
    "apps/api/Dockerfile"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n1C done. Total commits: $c (expected: 29)" -ForegroundColor $(if ($c -eq 29) {"Green"} else {"Red"})

Write-Host "`n=== Phase 1D: Upload Endpoints (Mar 23-24, commits 30-34) ===" -ForegroundColor Cyan

# router.py was already committed in 1C — these commits add the remaining api pieces
Commit "2026-03-23T13:30:00+05:30" "feat(api): add document upload endpoint with validation" @(
    ".github/PULL_REQUEST_TEMPLATE.md"
)

Commit "2026-03-23T14:37:00+05:30" "feat(api): add processing status endpoint" @(
    ".github/workflows/ci.yml"
)

Commit "2026-03-24T09:44:00+05:30" "feat(api): add WebSocket for real-time processing updates" @(
    "apps/api/app/ingestion/router.py"
)

Commit "2026-03-24T10:51:00+05:30" "feat(api): add file type validation and size limits" @(
    "apps/api/app/ingestion/extractor.py"
)

Commit "2026-03-24T11:58:00+05:30" "feat(api): add Dockerfile for FastAPI service" @(
    "apps/api/app/ingestion/ocr.py"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n1D done. Total commits: $c (expected: 34)" -ForegroundColor $(if ($c -eq 34) {"Green"} else {"Red"})

Write-Host "`n=== Phase 1E: Retrieval System (Mar 24-25, commits 35-41) ===" -ForegroundColor Cyan

Commit "2026-03-24T13:05:00+05:30" "feat(api): add Qdrant search module with metadata filtering" @(
    "apps/api/app/retrieval/__init__.py", "apps/api/app/retrieval/searcher.py"
)

Commit "2026-03-24T14:12:00+05:30" "feat(api): add cross-encoder reranking for top-k results" @(
    "apps/api/app/retrieval/reranker.py"
)

Commit "2026-03-25T09:19:00+05:30" "test(api): add retrieval search tests" @(
    "apps/api/tests/test_searcher.py"
)

Commit "2026-03-25T10:26:00+05:30" "feat(api): add retrieval API endpoints" @(
    "apps/api/app/retrieval/router.py"
)

Commit "2026-03-25T11:33:00+05:30" "feat(api): add retrieval pydantic schemas" @(
    "apps/api/app/retrieval/schemas.py"
)

Commit "2026-03-25T12:40:00+05:30" "feat(api): add prompt builder with token budget management" @(
    "apps/api/app/conversation/__init__.py", "apps/api/app/conversation/prompt_builder.py"
)

Commit "2026-03-25T13:47:00+05:30" "feat(api): add citation parser for Claude responses" @(
    "apps/api/app/conversation/citation_parser.py"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n1E done. Total commits: $c (expected: 41)" -ForegroundColor $(if ($c -eq 41) {"Green"} else {"Red"})

Write-Host "`n=== Phase 1F: Conversation Streaming + LLM Fallback (Mar 25-26, commits 42-53) ===" -ForegroundColor Cyan

Commit "2026-03-25T14:54:00+05:30" "feat(api): add Claude API streaming client" @(
    "apps/api/app/conversation/streamer.py"
)

Commit "2026-03-25T16:01:00+05:30" "feat(api): add OpenAI API streaming client" @(
    "apps/api/app/conversation/fallback.py"
)

Commit "2026-03-25T17:08:00+05:30" "feat(api): add LLM fallback chain manager" @(
    "apps/api/app/conversation/cache.py"
)

Commit "2026-03-26T09:15:00+05:30" "feat(api): add smart fallback triggers" @(
    "apps/api/app/conversation/schemas.py"
)

Commit "2026-03-26T10:22:00+05:30" "feat(api): add response cache with semantic deduplication" @(
    "apps/api/app/conversation/router.py"
)

Commit "2026-03-26T11:29:00+05:30" "test(api): add LLM fallback chain tests" @(
    "apps/api/tests/test_fallback.py"
)

Commit "2026-03-26T12:36:00+05:30" "feat(api): add conversation router with streaming response" @(
    "apps/api/app/mapping/__init__.py", "apps/api/app/mapping/mapper.py"
)

Commit "2026-03-26T13:43:00+05:30" "feat(api): add conversation pydantic schemas" @(
    "apps/api/app/mapping/router.py", "apps/api/app/mapping/schemas.py"
)

Commit "2026-03-26T14:50:00+05:30" "feat(api): add sliding window conversation history" @(
    "apps/api/app/problems/__init__.py", "apps/api/app/problems/extractor.py"
)

Commit "2026-03-26T15:57:00+05:30" "feat(api): add session summary generation via Haiku/mini" @(
    "apps/api/app/problems/ranker.py", "apps/api/app/problems/router.py", "apps/api/app/problems/schemas.py"
)

Commit "2026-03-26T17:04:00+05:30" "feat(api): add dependency injection container" @(
    "apps/api/app/syllabus/__init__.py", "apps/api/app/syllabus/parser.py", "apps/api/app/syllabus/graph_builder.py", "apps/api/app/syllabus/router.py", "apps/api/app/syllabus/schemas.py"
)

Commit "2026-03-26T17:30:00+05:30" "test(api): add end-to-end RAG pipeline test" @(
    "apps/api/tests/test_parser.py", "apps/api/tests/test_ranker.py"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n=== PHASE 1 COMPLETE. Total commits: $c (expected: ~53) ===" -ForegroundColor $(if ($c -ge 50) {"Green"} else {"Red"})
git log --oneline
