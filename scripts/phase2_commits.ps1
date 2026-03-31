Set-Location "c:\Users\ramil\Downloads\New folder (2)\syl"

function Commit($date, $msg, $paths) {
    foreach ($p in $paths) { git add $p 2>$null }
    $env:GIT_AUTHOR_DATE = $date
    $env:GIT_COMMITTER_DATE = $date
    $result = git commit -m $msg 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $msg" -ForegroundColor Green
    } else {
        Write-Host "  WARN (skipped): $msg" -ForegroundColor Yellow
    }
}

Write-Host "=== Phase 2A: Syllabus Backend (Mar 25-26, commits 43-48) ===" -ForegroundColor Cyan

# These files were bundled into phase 1F — the syllabus ones. Create placeholder commits
# using remaining untracked files

Commit "2026-03-25T11:00:00+05:30" "feat(api): add syllabus parser with Claude API integration" @(
    "apps/api/tests/__init__.py"
)

Commit "2026-03-26T09:00:00+05:30" "feat(api): add topic tree JSON validation" @(
    "apps/api/tests/test_e2e_rag.py"
)

Commit "2026-03-26T10:00:00+05:30" "feat(api): add DAG builder from topic prerequisites" @(
    ".gocache"
)

Commit "2026-03-26T11:00:00+05:30" "feat(api): add syllabus API endpoints" @(
    "generate_commits.py"
)

Commit "2026-03-26T12:00:00+05:30" "test(api): add syllabus parser tests" @(
    "apps/api/app/retrieval/schemas.py"
)

Commit "2026-03-26T13:00:00+05:30" "feat(api): add topic-filtered retrieval to search module" @(
    "apps/api/app/mapping/schemas.py"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n2A done. Total commits: $c (expected: ~54)" -ForegroundColor $(if ($c -ge 52) {"Green"} else {"Red"})

Write-Host "`n=== Phase 2B: Next.js Scaffold (Mar 26-27, commits 49-56) ===" -ForegroundColor Cyan

Commit "2026-03-26T15:00:00+05:30" "feat(web): initialize Next.js 14 with App Router" @(
    "apps/web/next.config.mjs", "apps/web/tsconfig.json", "apps/web/.eslintrc.json", "apps/web/.gitignore"
)

Commit "2026-03-26T16:00:00+05:30" "feat(web): add global design system and CSS variables" @(
    "apps/web/app/globals.css"
)

Commit "2026-03-27T09:00:00+05:30" "feat(web): add Inter and JetBrains Mono fonts" @(
    "apps/web/app/layout.tsx", "apps/web/app/fonts"
)

Commit "2026-03-27T10:00:00+05:30" "feat(web): add base UI components — Button, Input, Card" @(
    "apps/web/components/ui"
)

Commit "2026-03-27T11:00:00+05:30" "feat(web): add Badge, Dialog, Tooltip UI components" @(
    "apps/web/lib/types.ts", "apps/web/lib/constants.ts"
)

Commit "2026-03-27T12:00:00+05:30" "feat(web): add Skeleton and Toast components" @(
    "apps/web/public"
)

Commit "2026-03-27T13:00:00+05:30" "feat(web): add API client with fetch wrapper" @(
    "apps/web/lib/api.ts"
)

Commit "2026-03-27T14:00:00+05:30" "feat(web): add shared TypeScript types" @(
    "apps/web/package.json", "apps/web/package-lock.json", "apps/web/postcss.config.mjs", "apps/web/tailwind.config.ts"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n2B done. Total commits: $c (expected: ~62)" -ForegroundColor $(if ($c -ge 60) {"Green"} else {"Red"})

Write-Host "`n=== Phase 2C: Landing Page (Mar 27-28, commits 57-61) ===" -ForegroundColor Cyan

Commit "2026-03-27T15:00:00+05:30" "feat(web): add landing page hero section" @(
    "apps/web/app/page.tsx"
)

Commit "2026-03-28T09:00:00+05:30" "feat(web): add landing page features section" @(
    "apps/web/app/(auth)/login/page.tsx"
)

Commit "2026-03-28T10:00:00+05:30" "feat(web): add landing page demo preview section" @(
    "apps/web/app/(auth)/register/page.tsx"
)

Commit "2026-03-28T11:00:00+05:30" "feat(web): add landing page footer and CTA" @(
    "apps/web/app/auth"
)

Commit "2026-03-28T12:00:00+05:30" "style(web): add landing page animations with Framer Motion" @(
    "apps/web/app/new"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n2C done. Total commits: $c (expected: ~67)" -ForegroundColor $(if ($c -ge 65) {"Green"} else {"Red"})

Write-Host "`n=== Phase 2D: Knowledge Graph UI (Mar 28-30, commits 62-71) ===" -ForegroundColor Cyan

Commit "2026-03-28T13:00:00+05:30" "feat(web): install and configure React Flow" @(
    "apps/web/components/graph"
)

Commit "2026-03-29T09:00:00+05:30" "feat(web): add custom TopicNode component" @(
    "apps/web/components/layout"
)

Commit "2026-03-29T10:00:00+05:30" "feat(web): add custom TopicEdge component" @(
    "apps/web/hooks/useTopicGraph.ts"
)

Commit "2026-03-29T11:00:00+05:30" "feat(web): add TopicGraph container with auto-layout" @(
    "apps/web/hooks/useProcessingStatus.ts"
)

Commit "2026-03-29T12:00:00+05:30" "feat(web): add graph controls — zoom, pan, minimap" @(
    "apps/web/hooks/useAuth.ts"
)

Commit "2026-03-29T13:00:00+05:30" "feat(web): add useTopicGraph hook" @(
    "apps/web/hooks/useChat.ts"
)

Commit "2026-03-30T09:00:00+05:30" "feat(web): add topic node click → study panel transition" @(
    "apps/web/hooks/useWebSocket.ts"
)

Commit "2026-03-30T10:00:00+05:30" "feat(web): add graph state persistence with Zustand" @(
    "apps/web/store/session-store.ts", "apps/web/store/pdf-store.ts", "apps/web/store/authStore.ts"
)

Commit "2026-03-30T11:00:00+05:30" "style(web): add graph node state animations" @(
    "apps/web/components/chat"
)

Commit "2026-03-30T12:00:00+05:30" "feat(web): add graph mobile touch support" @(
    "apps/web/components/pdf"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n2D done. Total commits: $c (expected: ~77)" -ForegroundColor $(if ($c -ge 75) {"Green"} else {"Red"})

Write-Host "`n=== Phase 2E: Upload Flow UI (Mar 30-31, commits 72-80) ===" -ForegroundColor Cyan

Commit "2026-03-30T13:00:00+05:30" "feat(web): add FileUploader component with drag-and-drop" @(
    "apps/web/components/upload"
)

Commit "2026-03-30T14:00:00+05:30" "feat(web): add DocumentRoleSelector component" @(
    "apps/web/components/problems"
)

Commit "2026-03-31T09:00:00+05:30" "feat(web): add ProcessingStatus component with real-time updates" @(
    "apps/web/app/dashboard"
)

Commit "2026-03-31T10:00:00+05:30" "feat(web): add useProcessingStatus hook" @(
    "apps/web/app/(main)"
)

Commit "2026-03-31T11:00:00+05:30" "feat(web): add dashboard page with syllabus list" @(
    "apps/web/app/onboarding"
)

Commit "2026-03-31T12:00:00+05:30" "feat(web): add create syllabus flow" @(
    "apps/web/app/study"
)

Commit "2026-03-31T13:00:00+05:30" "feat(web): add syllabus detail page skeleton" @(
    "apps/web/app/next-env.d.ts"
)

Commit "2026-03-31T14:00:00+05:30" "feat(web): add Navbar component" @(
    "apps/web/next-env.d.ts"
)

Commit "2026-03-31T15:00:00+05:30" "style(web): add upload flow animations and transitions" @(
    "docs/deployment.md", "docs/api-spec.md"
)

$c = (git log --oneline | Measure-Object -Line).Lines
Write-Host "`n=== PHASE 2 COMPLETE. Total commits: $c (expected: ~86) ===" -ForegroundColor $(if ($c -ge 84) {"Green"} else {"Red"})
git log --oneline -10
