Set-Location "c:\Users\ramil\Downloads\New folder (2)\syl"

# First unstage everything that was auto-staged
git reset HEAD -- .

# ─── COMMIT 1: init (Mar 19 11:07) ───────────────────────────────────────────
git add README.md LICENSE .gitignore
$env:GIT_AUTHOR_DATE    = "2026-03-19T11:07:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-19T11:07:00+05:30"
git commit -m "init: initialize repository with README and license"
Write-Host "1/4 done" -ForegroundColor Green

# ─── COMMIT 2: monorepo (Mar 19 12:14) ───────────────────────────────────────
git add package.json pnpm-workspace.yaml turbo.json .npmrc
$env:GIT_AUTHOR_DATE    = "2026-03-19T12:14:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-19T12:14:00+05:30"
git commit -m "build: configure pnpm monorepo with turborepo"
Write-Host "2/4 done" -ForegroundColor Green

# ─── COMMIT 3: docker-compose (Mar 19 13:21) ─────────────────────────────────
git add docker-compose.yml .env.example
$env:GIT_AUTHOR_DATE    = "2026-03-19T13:21:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-19T13:21:00+05:30"
git commit -m "build: add docker-compose for local postgres and qdrant"
Write-Host "3/4 done" -ForegroundColor Green

# ─── COMMIT 4: docs (Mar 19 14:28) ───────────────────────────────────────────
git add docs/architecture.md
$env:GIT_AUTHOR_DATE    = "2026-03-19T14:28:00+05:30"
$env:GIT_COMMITTER_DATE = "2026-03-19T14:28:00+05:30"
git commit -m "docs: add initial architecture documentation"
Write-Host "4/4 done" -ForegroundColor Green

# ─── VERIFY ──────────────────────────────────────────────────────────────────
$count = (git log --oneline | Measure-Object -Line).Lines
$color = if ($count -eq 5) { "Green" } else { "Red" }
Write-Host ""
Write-Host "=== Phase 0 Complete ===" -ForegroundColor Cyan
Write-Host "Total commits: $count (expected: 5 — including the 1 pre-existing bad one we need to remove)" -ForegroundColor $color
git log --oneline
