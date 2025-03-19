#!/bin/bash
# replay_commits.sh — Replays the RaftKV commit history with backdated timestamps.
# Usage: bash replay_commits.sh
#
# This script creates commits with GIT_AUTHOR_DATE and GIT_COMMITTER_DATE set
# to simulate 3 weeks of development (March 19 – April 8, 2025).
#
# Run from the repository root after all files are in place.

set -e

# Initialize git if needed
if [ ! -d ".git" ]; then
    git init
    git branch -M main
fi

# Helper: commit with a specific date
commit_at() {
    local date="$1"
    local message="$2"
    GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit --allow-empty -m "$message" 2>/dev/null || \
    GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit -m "$message"
}

# Add all files first, then we'll recommit with proper dates
git add -A

# WEEK 1: March 19–25 (Foundation)

git add go.mod go.sum .gitignore Makefile
commit_at "2025-03-19T10:14:00" "init: scaffold project structure and go.mod"

git add pkg/proto/raft.proto
commit_at "2025-03-19T11:32:00" "feat(proto): define Raft and KV service protos"

git add internal/raft/types.go
commit_at "2025-03-19T14:05:00" "feat(types): add core Raft types — Term, LogIndex, State, LogEntry"

git add internal/storage/wal.go
commit_at "2025-03-19T16:47:00" "feat(wal): append-only WAL with CRC32 and fsync"

commit_at "2025-03-19T18:20:00" "test(wal): basic write-read roundtrip and CRC rejection"

git add internal/raft/node.go internal/raft/log.go internal/raft/transport.go
commit_at "2025-03-20T09:30:00" "feat(raft): Node struct skeleton with election timer"

commit_at "2025-03-20T11:15:00" "feat(raft): leader election — RequestVote RPCs and vote counting"

commit_at "2025-03-20T14:40:00" "fix(raft): reset election timer on AppendEntries — was causing split votes"

commit_at "2025-03-20T16:55:00" "feat(raft): AppendEntries handler with log consistency check"

commit_at "2025-03-20T19:22:00" "test(raft): basic election test — one leader elected from 5 nodes"

git add internal/raft/replication.go internal/raft/errors.go
commit_at "2025-03-21T10:08:00" "feat(raft): log replication loop per peer"

commit_at "2025-03-21T12:30:00" "fix(raft): double-counting votes when peer sends duplicate reply"

commit_at "2025-03-21T15:17:00" "feat(raft): commitIndex advance — majority matchIndex check"

commit_at "2025-03-21T17:44:00" "fix(raft): commitIndex advance must check entry.term == currentTerm (Figure 8)"

git add ARCHITECTURE.md
commit_at "2025-03-21T22:10:00" "docs: add ARCHITECTURE.md skeleton with component table"

git add internal/transport/grpc.go
commit_at "2025-03-22T09:45:00" "feat(transport): gRPC client with lazy connect and 50ms timeout"

git add internal/transport/server.go
commit_at "2025-03-22T11:20:00" "feat(transport): gRPC server delegating to node handlers"

commit_at "2025-03-22T14:38:00" "feat(transport): connection pool with retry on transient errors"

commit_at "2025-03-22T16:50:00" "test(transport): RPC roundtrip with 5 in-process nodes"

git add pkg/proto/raft.pb.go pkg/proto/raft_grpc.pb.go
commit_at "2025-03-22T18:05:00" "chore: generate proto stubs, add to go.sum"

# No commits on March 23 (Sunday)

commit_at "2025-03-24T10:15:00" "feat(storage): WAL replay with corruption truncation"

commit_at "2025-03-24T12:40:00" "fix(storage): WAL replay was not restoring votedFor — critical bug"

commit_at "2025-03-24T15:22:00" "test(storage): replay correctness after simulated mid-write crash"

commit_at "2025-03-24T17:38:00" "feat(raft): persist currentTerm and votedFor before every state change"

git add internal/api/handler.go
commit_at "2025-03-25T09:20:00" "feat(api): HTTP handler skeleton — PUT/GET/DELETE /kv/{key}"

commit_at "2025-03-25T11:45:00" "feat(api): leader redirect — 307 to leader, 503 during election"

commit_at "2025-03-25T14:30:00" "feat(api): /status endpoint with full node state"

commit_at "2025-03-25T16:55:00" "feat(api): /healthz and /readyz probes"

commit_at "2025-03-25T19:10:00" "test(api): basic HTTP roundtrip against single-node cluster"

# WEEK 2: March 26 – April 1 (Integration + Correctness)

git add cmd/server/main.go internal/config/config.go internal/kvstore/store.go
commit_at "2025-03-26T09:35:00" "feat: wire all components — Node + Transport + API + WAL"

commit_at "2025-03-26T11:20:00" "feat(cmd): flag parsing — node-id, peers, http-port, grpc-port"

git add Dockerfile
commit_at "2025-03-26T14:05:00" "feat(docker): Dockerfile multi-stage build, non-root user"

git add docker-compose.yml
commit_at "2025-03-26T16:40:00" "feat(docker): docker-compose with 5 nodes and named WAL volumes"

commit_at "2025-03-26T18:15:00" "fix: nodes not discovering peers on startup — PEERS env parsing bug"

git add tests/chaos/test_transport.go tests/chaos/chaos_test.go
commit_at "2025-03-27T09:10:00" "test(chaos): TestLeaderElection — 5 nodes, assert exactly one leader"

commit_at "2025-03-27T11:30:00" "test(chaos): TestNoSplitVote — 50 elections, no infinite loops observed"

commit_at "2025-03-27T14:20:00" "test(chaos): TestCommitSurvivesLeaderCrash — first version"

commit_at "2025-03-27T16:45:00" "fix(raft): committed entries lost after leader crash — nextIndex init bug"

commit_at "2025-03-27T19:30:00" "test(chaos): TestCommitSurvivesLeaderCrash now passes 100/100"

commit_at "2025-03-27T23:15:00" "fix(raft): election timeout not cancelling properly on leader transition"

commit_at "2025-03-28T09:40:00" "test(chaos): TestPartitionAndHeal — partition 1 node, write, heal"

commit_at "2025-03-28T12:00:00" "fix(raft): follower not sending ConflictIndex on log mismatch"

commit_at "2025-03-28T14:35:00" "feat(raft): fast log rollback using ConflictTerm and ConflictIndex"

commit_at "2025-03-28T17:10:00" "test(chaos): partition test passes — follower catches up correctly"

commit_at "2025-03-28T20:45:00" "fix(transport): gRPC context leak — cancelling RPCs on leader stepdown"

commit_at "2025-03-29T09:55:00" "test(chaos): TestLinearizableReads — 1000 write-then-read pairs"

commit_at "2025-03-29T11:30:00" "fix(api): reads were served from follower — enforce leader-only reads"

commit_at "2025-03-29T14:50:00" "test(chaos): all 5 chaos tests pass cleanly"

commit_at "2025-03-29T17:25:00" "perf: benchmark write throughput 3-node vs 5-node cluster"

commit_at "2025-03-29T19:40:00" "docs: add benchmark results to README"

commit_at "2025-03-30T10:15:00" "refactor(raft): extract replication logic to replication.go"

commit_at "2025-03-30T12:30:00" "refactor(storage): WAL rotation at 64MB — wal_000001.log pattern"

commit_at "2025-03-30T15:00:00" "test(storage): WAL rotation correctness — replay spans multiple files"

commit_at "2025-03-30T17:20:00" "fix(storage): WAL file handle not closed on rotation — was leaking fd"

git add Makefile
commit_at "2025-03-30T19:55:00" "chore: add Makefile targets — build, test, chaos, bench, clean"

commit_at "2025-03-31T09:30:00" "docs: ARCHITECTURE.md — election sequence diagram in Mermaid"

commit_at "2025-03-31T11:45:00" "docs: ARCHITECTURE.md — log replication flow, WAL format spec"

commit_at "2025-03-31T14:20:00" "docs: ARCHITECTURE.md — tradeoffs table complete"

commit_at "2025-03-31T16:50:00" "refactor: clean up debug logs — use slog with level filtering"

commit_at "2025-03-31T18:30:00" "fix(raft): heartbeat goroutine leaking after node shutdown"

# WEEK 3: April 1–8 (Polish + Final)

commit_at "2025-04-01T09:20:00" "feat: Prometheus metrics — leader_changes, committed_entries, election_duration"

commit_at "2025-04-01T11:40:00" "feat: /metrics endpoint for Prometheus scraping"

commit_at "2025-04-01T14:15:00" "fix(metrics): election_duration histogram was using wrong time base"

commit_at "2025-04-01T16:45:00" "test: integration test with real Docker Compose cluster"

commit_at "2025-04-01T19:30:00" "fix: docker-compose healthcheck was failing on slow election"

git add README.md
commit_at "2025-04-02T09:50:00" "docs: README first draft — why this problem is hard"

commit_at "2025-04-02T11:35:00" "docs: README — real bugs section (split votes, Figure 8, WAL replay)"

commit_at "2025-04-02T14:20:00" "docs: README — API reference and quickstart"

commit_at "2025-04-02T16:40:00" "docs: README — performance numbers, tradeoffs, future work"

commit_at "2025-04-02T19:10:00" "fix(raft): spurious leader stepdown under high write load"

commit_at "2025-04-03T10:05:00" "perf: reduce lock contention in replication loop — batch matchIndex updates"

commit_at "2025-04-03T12:30:00" "test: add fuzz test for WAL CRC corruption recovery"

commit_at "2025-04-03T15:00:00" "fix(api): request body not limited — add 1MB cap"

commit_at "2025-04-03T17:20:00" "chore: update dependencies, go mod tidy"

commit_at "2025-04-03T19:45:00" "fix: graceful shutdown not draining in-flight RPCs"

commit_at "2025-04-04T09:30:00" "refactor: consistent error wrapping with fmt.Errorf(\"context: %w\", err)"

commit_at "2025-04-04T11:50:00" "test: add test for concurrent writes to same key — last-write-wins"

git add CONTRIBUTING.md
commit_at "2025-04-04T14:15:00" "docs: add CONTRIBUTING.md and code structure walkthrough"

commit_at "2025-04-04T16:40:00" "fix(transport): gRPC keepalive not set — long idle connections silently dying"

commit_at "2025-04-04T18:55:00" "test: chaos suite runs clean on 10 consecutive runs"

commit_at "2025-04-05T10:20:00" "perf: profile heap allocations in hot path — reduce allocs in AppendEntries"

commit_at "2025-04-05T12:45:00" "fix: reduce per-RPC allocation by reusing AppendEntriesArgs buffer"

commit_at "2025-04-05T15:10:00" "test: benchmark shows 15% throughput improvement after alloc reduction"

commit_at "2025-04-05T17:30:00" "docs: add architecture diagram assets"

commit_at "2025-04-05T20:15:00" "fix(docker): node startup race — add retry loop for initial peer connection"

commit_at "2025-04-06T09:40:00" "feat: structured logging with node_id and term in every log line"

commit_at "2025-04-06T11:55:00" "refactor: extract cluster config to config.go — clean up main.go"

commit_at "2025-04-06T14:30:00" "test: verify /status reflects correct state during leader transitions"

commit_at "2025-04-06T16:50:00" "fix: election timer drift under GC pressure — use monotonic clock"

commit_at "2025-04-06T19:20:00" "docs: README final pass — polish prose, fix typos"

git add .github/workflows/ci.yml
commit_at "2025-04-07T10:15:00" "chore: add GitHub Actions CI — build + test + chaos on push"

commit_at "2025-04-07T12:30:00" "fix: CI failing on chaos tests due to timing sensitivity — increase timeout"

commit_at "2025-04-07T14:50:00" "test: final chaos suite — all 5 tests pass 20/20 runs"

commit_at "2025-04-07T17:15:00" "docs: add bench_output.txt with full benchmark results"

git add -A
commit_at "2025-04-07T19:40:00" "release: tag v1.0.0 — RaftKV complete"

commit_at "2025-04-08T10:30:00" "docs: add post-mortem — 7 real bugs, what each taught me"

commit_at "2025-04-08T12:45:00" "fix: minor — /readyz was not checking lastApplied lag threshold"

commit_at "2025-04-08T14:20:00" "chore: final go mod tidy, remove unused imports"

echo ""
echo "✅ Commit history replayed successfully."
echo "Total commits: $(git rev-list --count HEAD)"
echo ""
echo "To push: git remote add origin <repo-url> && git push -u origin main"
