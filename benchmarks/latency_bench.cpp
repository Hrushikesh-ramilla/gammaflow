// ─────────────────────────────────────────────────────────────────────────────
// GammaFlow — latency_bench.cpp
// High-resolution end-to-end latency benchmark.
//
// Pushes 1,000,000 RiskEvents through the SPSC ring buffer → RiskEvaluator
// pipeline and measures per-event latency using std::chrono nanosecond
// timestamps.  Reports average, median, p95, p99, and p99.9 latencies.
// ─────────────────────────────────────────────────────────────────────────────

#include "ring_buffer.hpp"
#include "evaluator.hpp"
#include "models.hpp"
#include "types.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <thread>
#include <vector>

// ── Configuration ───────────────────────────────────────────────────────────

static constexpr std::size_t NUM_EVENTS      = 1'000'000;
static constexpr std::size_t RING_CAPACITY   = 65536;   // Must be power of two.
static constexpr std::size_t WARMUP_EVENTS   = 10'000;  // Discard first N for JIT/cache warm-up.

// ── Helpers ─────────────────────────────────────────────────────────────────

using Clock     = std::chrono::high_resolution_clock;
using TimePoint = Clock::time_point;
using Nanos     = std::chrono::nanoseconds;

/// Build a synthetic RiskEvent with varying fields to exercise different
/// evaluator code paths and prevent the optimizer from constant-folding.
static gammaflow::RiskEvent make_event(std::uint64_t seq) {
    gammaflow::RiskEvent ev{};
    ev.id           = seq;
    ev.timestamp_ns = static_cast<std::int64_t>(
        std::chrono::duration_cast<Nanos>(
            Clock::now().time_since_epoch()).count());

    // Rotate through a set of instruments.
    static constexpr std::array<const char*, 4> symbols = {
        "AAPL", "TSLA", "GOOG", "AMZN"
    };
    const char* sym = symbols[seq % symbols.size()];
    std::memset(ev.instrument.data(), 0, ev.instrument.size());
    std::memcpy(ev.instrument.data(), sym, std::strlen(sym));

    // Vary price and quantity to hit different evaluator branches.
    // Price oscillates: 0.50, 5.00, 50.00, 500.00, 5000.00
    static constexpr std::array<std::int64_t, 5> prices = {
         50000000LL,       //   0.50  (penny stock)
        500000000LL,       //   5.00  (low price)
       5000000000LL,       //  50.00  (mid price)
      50000000000LL,       // 500.00  (high price)
     500000000000LL,       // 5000.00 (ultra-high)
    };
    ev.price = gammaflow::Price::from_raw(prices[seq % prices.size()]);

    // Quantity oscillates: 5, 50, 5000, 50000, 500000
    static constexpr std::array<std::int64_t, 5> quantities = {
           50000LL,   //       5
          500000LL,   //      50
        50000000LL,   //    5000
       500000000LL,   //   50000
      5000000000LL,   //  500000
    };
    ev.quantity = gammaflow::Quantity::from_raw(quantities[seq % quantities.size()]);

    return ev;
}

/// Print a formatted latency line.
static void print_stat(const char* label, std::int64_t ns) {
    std::cout << "  " << std::left << std::setw(22) << label
              << std::right << std::setw(10) << ns << " ns";
    if (ns < 1'000) {
        std::cout << "  (" << ns << " ns)";
    } else if (ns < 1'000'000) {
        std::cout << "  (" << std::fixed << std::setprecision(2)
                  << (ns / 1'000.0) << " µs)";
    } else {
        std::cout << "  (" << std::fixed << std::setprecision(2)
                  << (ns / 1'000'000.0) << " ms)";
    }
    std::cout << "\n";
}

// ═════════════════════════════════════════════════════════════════════════════
// Benchmark 1: Evaluator-only (single-threaded, no ring buffer)
//
// Measures the raw cost of RiskEvaluator::evaluate() in isolation, free of
// any inter-thread synchronization overhead.
// ═════════════════════════════════════════════════════════════════════════════

static void bench_evaluator_only() {
    std::cout << "── Benchmark 1: Evaluator-only (single-threaded) ──\n\n";

    gammaflow::RiskEvaluator evaluator;
    std::vector<std::int64_t> latencies;
    latencies.reserve(NUM_EVENTS);

    // Pre-generate events to keep allocation out of the timed region.
    std::vector<gammaflow::RiskEvent> events(NUM_EVENTS);
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        events[i] = make_event(i);
    }

    // Warm-up pass (results discarded).
    for (std::size_t i = 0; i < WARMUP_EVENTS && i < NUM_EVENTS; ++i) {
        volatile auto r = evaluator.evaluate(events[i]);
        (void)r;
    }

    // Timed pass.
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        auto t0 = Clock::now();
        volatile auto result = evaluator.evaluate(events[i]);
        auto t1 = Clock::now();
        (void)result;

        latencies.push_back(
            std::chrono::duration_cast<Nanos>(t1 - t0).count());
    }

    // ── Statistics ───────────────────────────────────────────────────────
    std::sort(latencies.begin(), latencies.end());

    std::int64_t sum = 0;
    for (auto l : latencies) sum += l;

    auto percentile = [&](double p) -> std::int64_t {
        auto idx = static_cast<std::size_t>(p * latencies.size());
        if (idx >= latencies.size()) idx = latencies.size() - 1;
        return latencies[idx];
    };

    print_stat("Average",     sum / static_cast<std::int64_t>(latencies.size()));
    print_stat("Median (p50)", percentile(0.50));
    print_stat("p95",          percentile(0.95));
    print_stat("p99",          percentile(0.99));
    print_stat("p99.9",        percentile(0.999));
    print_stat("Min",          latencies.front());
    print_stat("Max",          latencies.back());

    std::cout << "\n  Events evaluated: " << NUM_EVENTS << "\n\n";
}

// ═════════════════════════════════════════════════════════════════════════════
// Benchmark 2: End-to-end (producer → SPSC ring → evaluator, two threads)
//
// Measures the full pipeline latency including ring buffer push/pop and
// cross-thread synchronization.
// ═════════════════════════════════════════════════════════════════════════════

static void bench_end_to_end() {
    std::cout << "── Benchmark 2: End-to-end (producer → ring → evaluator) ──\n\n";

    gammaflow::SPSCRingBuffer<const gammaflow::RiskEvent*, RING_CAPACITY> ring;
    gammaflow::RiskEvaluator evaluator;

    // Shared latency storage: producer writes send_ts into the event's
    // timestamp_ns field; consumer reads it back to compute delta.
    std::vector<std::int64_t> latencies(NUM_EVENTS, 0);
    std::atomic<bool> consumer_done{false};

    // Pre-generate events.
    std::vector<gammaflow::RiskEvent> events(NUM_EVENTS);
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        events[i] = make_event(i);
    }

    // ── Consumer thread ─────────────────────────────────────────────────
    std::thread consumer([&] {
        std::size_t count = 0;
        while (count < NUM_EVENTS) {
            auto maybe = ring.try_pop();
            if (maybe.has_value()) {
                const gammaflow::RiskEvent* ev = *maybe;

                // Evaluate.
                volatile auto result = evaluator.evaluate(*ev);
                (void)result;

                // Measure latency: now – send timestamp.
                auto now_ns = std::chrono::duration_cast<Nanos>(
                    Clock::now().time_since_epoch()).count();

                if (count >= WARMUP_EVENTS) {
                    latencies[count] = now_ns - ev->timestamp_ns;
                }

                ++count;
            } else {
                std::this_thread::yield();
            }
        }
        consumer_done.store(true, std::memory_order_release);
    });

    // ── Producer (this thread) ──────────────────────────────────────────
    auto next_tick = Clock::now();
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        // Spin-wait to simulate a realistic network line rate (~1M msgs/sec)
        // This prevents the ring buffer from filling instantly.
        if (i > 0) {
            next_tick += std::chrono::microseconds(1);
            while (Clock::now() < next_tick) {
                // busy spin to prevent CPU sleep (mimics NIC polling)
            }
        } else {
            next_tick = Clock::now();
        }

        // Stamp the send time just before pushing.
        events[i].timestamp_ns = static_cast<std::int64_t>(
            std::chrono::duration_cast<Nanos>(
                Clock::now().time_since_epoch()).count());

        while (!ring.try_push(&events[i])) {
            std::this_thread::yield();  // Back-pressure.
        }
    }

    consumer.join();

    // ── Statistics ───────────────────────────────────────────────────────
    auto valid_begin = latencies.begin() + WARMUP_EVENTS;
    auto valid_end = latencies.end();
    std::size_t valid_count = NUM_EVENTS - WARMUP_EVENTS;

    std::sort(valid_begin, valid_end);

    std::int64_t sum = 0;
    for (auto it = valid_begin; it != valid_end; ++it) sum += *it;

    auto percentile = [&](double p) -> std::int64_t {
        auto idx = static_cast<std::size_t>(p * valid_count);
        if (idx >= valid_count) idx = valid_count - 1;
        return *(valid_begin + idx);
    };

    print_stat("Average",      sum / static_cast<std::int64_t>(valid_count));
    print_stat("Median (p50)", percentile(0.50));
    print_stat("p95",          percentile(0.95));
    print_stat("p99",          percentile(0.99));
    print_stat("p99.9",        percentile(0.999));
    print_stat("Min",          *valid_begin);
    print_stat("Max",          *(valid_end - 1));

    std::cout << "\n  Events processed: " << valid_count << " (excluding " << WARMUP_EVENTS << " warmup)\n\n";
}

// ═════════════════════════════════════════════════════════════════════════════
// Benchmark 3: Throughput (events / second)
// ═════════════════════════════════════════════════════════════════════════════

static void bench_throughput() {
    std::cout << "── Benchmark 3: Throughput (events/sec) ──\n\n";

    gammaflow::RiskEvaluator evaluator;

    std::vector<gammaflow::RiskEvent> events(NUM_EVENTS);
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        events[i] = make_event(i);
    }

    auto t0 = Clock::now();
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        volatile auto result = evaluator.evaluate(events[i]);
        (void)result;
    }
    auto t1 = Clock::now();

    auto elapsed_ns = std::chrono::duration_cast<Nanos>(t1 - t0).count();
    double elapsed_s = static_cast<double>(elapsed_ns) / 1e9;
    double events_per_sec = NUM_EVENTS / elapsed_s;

    std::cout << "  Total time:       " << std::fixed << std::setprecision(3)
              << (elapsed_ns / 1e6) << " ms\n";
    std::cout << "  Throughput:       " << std::fixed << std::setprecision(0)
              << events_per_sec << " events/sec\n";
    std::cout << "  Avg ns/event:     " << (elapsed_ns / static_cast<std::int64_t>(NUM_EVENTS))
              << " ns\n\n";
}

// ═════════════════════════════════════════════════════════════════════════════
// Main
// ═════════════════════════════════════════════════════════════════════════════

int main() {
    std::cout << "\n"
              << "╔══════════════════════════════════════════════════════════╗\n"
              << "║         GammaFlow — Latency Benchmarking Suite          ║\n"
              << "╠══════════════════════════════════════════════════════════╣\n"
              << "║  Events:    " << std::setw(10) << NUM_EVENTS
              << "                                ║\n"
              << "║  Ring Size: " << std::setw(10) << RING_CAPACITY
              << "                                ║\n"
              << "║  Warm-up:   " << std::setw(10) << WARMUP_EVENTS
              << "                                ║\n"
              << "╚══════════════════════════════════════════════════════════╝\n\n";

    bench_evaluator_only();
    bench_end_to_end();
    bench_throughput();

    std::cout << "══════════════════════════════════════════════════════════\n"
              << "  Benchmark complete.\n"
              << "══════════════════════════════════════════════════════════\n\n";

    return 0;
}
