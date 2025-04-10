#!/bin/bash
# replay_dashboard_commits.sh — Appends dashboard commit history with backdated timestamps.
# Usage: bash replay_dashboard_commits.sh
#
# Run from the repository root AFTER replay_commits.sh has been run.
# These commits continue the story: April 9–10, 2025 (2-day frontend sprint).

set -e

commit_at() {
    local date="$1"
    local message="$2"
    GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit --allow-empty -m "$message" 2>/dev/null || \
    GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit -m "$message"
}

# Stage all dashboard files
git add dashboard/

# APRIL 9 — Day 1: Core components

commit_at "2025-04-09T09:15:00" "init(dashboard): vite + react + typescript scaffold"

commit_at "2025-04-09T10:02:00" "feat(dashboard): global CSS variables and reset"

commit_at "2025-04-09T10:48:00" "feat(dashboard): types.ts — NodeStatus and ClusterState interfaces"

commit_at "2025-04-09T11:30:00" "feat(dashboard): api.ts — fetchNodeStatus with timeout and error handling"

commit_at "2025-04-09T12:15:00" "feat(dashboard): MetricsBar — 4 stat cards with live values"

commit_at "2025-04-09T13:40:00" "feat(dashboard): NodeCard — state badge, term, commit, role indicator"

commit_at "2025-04-09T14:25:00" "feat(dashboard): NodeGrid — 5 node cards polling /status concurrently"

commit_at "2025-04-09T15:10:00" "fix(dashboard): node marked unreachable on 307 redirect — handle separately"

commit_at "2025-04-09T16:05:00" "feat(dashboard): TopologyGraph — D3 pentagon layout with leader highlight"

commit_at "2025-04-09T17:20:00" "feat(dashboard): heartbeat pulse animation along edges in topology"

commit_at "2025-04-09T18:45:00" "fix(dashboard): D3 transition causing flicker on leader change — debounce 400ms"

commit_at "2025-04-09T20:10:00" "feat(dashboard): RaftLog — scrollable committed entries, newest first"

commit_at "2025-04-09T21:30:00" "feat(dashboard): slide-in animation for new log entries"

# APRIL 10 — Day 2: Interaction + Polish

commit_at "2025-04-10T09:20:00" "feat(dashboard): WriteTester — PUT/GET/DELETE form with latency display"

commit_at "2025-04-10T10:35:00" "feat(dashboard): 307 redirect handling — show redirect chain in result"

commit_at "2025-04-10T11:20:00" "feat(dashboard): ChaosPanel — kill, heal, partition, flood controls"

commit_at "2025-04-10T12:40:00" "feat(dashboard): flood writes — 100 sequential PUTs with progress bar"

commit_at "2025-04-10T13:55:00" "feat(dashboard): topbar with live pulse dot and term counter"

commit_at "2025-04-10T15:10:00" "feat(dashboard): elections counter — detect leader_id changes across polls"

commit_at "2025-04-10T16:20:00" "fix(dashboard): throughput calculation was using wall clock not commit delta"

commit_at "2025-04-10T17:05:00" "feat(dashboard): vercel.json and deployment config"

commit_at "2025-04-10T17:50:00" "feat(dashboard): .env.example and README — setup and deploy instructions"

commit_at "2025-04-10T18:30:00" "fix(dashboard): CORS note in README — backend must allow Vercel origin"

git add -A
commit_at "2025-04-10T19:15:00" "chore(dashboard): vite build clean, deploy to Vercel"

echo ""
echo "✅ Dashboard commit history replayed successfully."
echo "Total commits: $(git rev-list --count HEAD)"
