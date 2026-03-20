#pragma once

// ─────────────────────────────────────────────────────────────────────────────
// GammaFlow — engine.hpp
// Core execution engine that ties the ring buffer, object pool, and risk
// evaluator into a continuously running consumer pipeline.
//
// Architecture:
//   Producer (user thread)           Consumer (background thread)
//   ┌─────────────────┐              ┌──────────────────────┐
//   │  submit(event)  │─── SPSC ───▶│  poll → evaluate     │
//   └─────────────────┘   RingBuf   │  store RiskResult    │
//                                    └──────────────────────┘
// ─────────────────────────────────────────────────────────────────────────────

#include "ring_buffer.hpp"
#include "evaluator.hpp"
#include "models.hpp"

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <thread>

namespace gammaflow {

/// Default ring buffer depth — 64K slots (must be power of two).
inline constexpr std::size_t DEFAULT_RING_CAPACITY = 65536;

// ─────────────────────────────────────────────────────────────────────────────
// GammaEngine
//
// Owns:
//   • A lock-free SPSC ring buffer of RiskEvent pointers.
//   • A background consumer thread that continuously drains the buffer and
//     passes each event through the RiskEvaluator.
//   • An optional user-supplied callback invoked with every RiskResult.
//
// Thread model:
//   – Exactly ONE producer thread calls submit().
//   – Exactly ONE consumer thread (spawned internally) calls poll().
//   – The ring buffer enforces the SPSC contract.
// ─────────────────────────────────────────────────────────────────────────────

class GammaEngine {
public:
    /// Optional callback for processed results.
    using ResultCallback = std::function<void(const RiskResult&)>;

    /// Construct the engine.  Does NOT start the consumer thread until
    /// start() is called.
    explicit GammaEngine(ResultCallback on_result = nullptr);

    // Non-copyable, non-movable (owns a thread).
    GammaEngine(const GammaEngine&)            = delete;
    GammaEngine& operator=(const GammaEngine&) = delete;
    GammaEngine(GammaEngine&&)                 = delete;
    GammaEngine& operator=(GammaEngine&&)      = delete;

    /// Destructor — signals the consumer to stop and joins the thread.
    ~GammaEngine();

    // ── Lifecycle ───────────────────────────────────────────────────────────

    /// Spawn the background consumer thread.
    void start();

    /// Signal the consumer to stop and join the thread.
    void stop();

    /// Returns true if the consumer thread is running.
    [[nodiscard]] bool running() const noexcept;

    // ── Producer API (single thread only) ───────────────────────────────────

    /// Enqueue a RiskEvent pointer for evaluation.
    /// Returns false if the ring buffer is full (back-pressure).
    bool submit(const RiskEvent* event) noexcept;

    // ── Statistics ──────────────────────────────────────────────────────────

    /// Number of events successfully evaluated by the consumer.
    [[nodiscard]] std::uint64_t events_processed() const noexcept;

private:
    /// Main consumer loop — runs on the background thread.
    void consumer_loop();

    // ── Members ─────────────────────────────────────────────────────────────

    SPSCRingBuffer<const RiskEvent*, DEFAULT_RING_CAPACITY> ring_;
    RiskEvaluator                                           evaluator_;
    ResultCallback                                          on_result_;

    std::atomic<bool>        running_{false};
    std::atomic<std::uint64_t> processed_{0};
    std::thread              worker_;
};

} // namespace gammaflow
