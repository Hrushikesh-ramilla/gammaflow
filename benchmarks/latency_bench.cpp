// ─────────────────────────────────────────────────────────────────────────────
// GammaFlow — latency_bench.cpp
// High-resolution end-to-end latency benchmark.
//
// Pushes 1,000,000 RiskEvents through the SPSC ring buffer → RiskEvaluator
// pipeline and measures per-event latency using __rdtsc() CPU cycles.
// ─────────────────────────────────────────────────────────────────────────────

#include "ring_buffer.hpp"
#include "evaluator.hpp"
#include "models.hpp"
#include "types.hpp"

#ifdef _MSC_VER
#include <intrin.h>
#else
#include <x86intrin.h>
#endif

#ifdef _WIN32
#include <windows.h>
#endif

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <memory>
#include <thread>
#include <vector>

// ── Configuration ───────────────────────────────────────────────────────────

static constexpr std::size_t NUM_EVENTS      = 1'000'000;
static constexpr std::size_t RING_CAPACITY   = 65536;   // Must be power of two.
static constexpr std::size_t WARMUP_EVENTS   = 10'000;  // Discard first N for JIT warm-up.

// ── Helpers ─────────────────────────────────────────────────────────────────

using Clock     = std::chrono::high_resolution_clock;
using TimePoint = Clock::time_point;
using Nanos     = std::chrono::nanoseconds;

/// Calibrate TSC to nanoseconds logic using 100ms baseline.
static double get_tsc_to_ns_multiplier() {
    auto t0_chrono = Clock::now();
    std::uint64_t t0_tsc = __rdtsc();
    
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    
    std::uint64_t t1_tsc = __rdtsc();
    auto t1_chrono = Clock::now();
    
    std::uint64_t tsc_diff = t1_tsc - t0_tsc;
    std::uint64_t ns_diff = std::chrono::duration_cast<Nanos>(t1_chrono - t0_chrono).count();
    
    return static_cast<double>(ns_diff) / static_cast<double>(tsc_diff);
}

/// A perfectly padded structure to ensure exactly one event per cache line.
/// Eliminates false sharing between producer enqueue and consumer dequeue.
struct alignas(64) PaddedEvent {
    gammaflow::RiskEvent event;
    std::uint64_t enqueue_tsc;
};

// Check MSVC C4324 suppression works inside the ring buffer, but this struct
// itself is naturally 64-byte aligned. RiskEvent = 40 bytes + 8 bytes TSC = 48 bytes.
// alignas(64) forces it to 64 bytes total.
static_assert(sizeof(PaddedEvent) == 64, "PaddedEvent must exactly fill one cache line");


/// Build a synthetic RiskEvent with varying fields to exercise evaluator code paths.
static gammaflow::RiskEvent make_event(std::uint64_t seq) {
    gammaflow::RiskEvent ev{};
    ev.id = seq;
    ev.timestamp_ns = 0; // Not used in this benchmark anymore.

    static constexpr std::array<const char*, 4> symbols = {
        "AAPL", "TSLA", "GOOG", "AMZN"
    };
    const char* sym = symbols[seq % symbols.size()];
    std::memset(ev.instrument.data(), 0, ev.instrument.size());
    std::memcpy(ev.instrument.data(), sym, std::strlen(sym));

    static constexpr std::array<std::int64_t, 5> prices = {
         50000000LL,       //   0.50  (penny stock)
        500000000LL,       //   5.00  (low price)
       5000000000LL,       //  50.00  (mid price)
      50000000000LL,       // 500.00  (high price)
     500000000000LL,       // 5000.00 (ultra-high)
    };
    ev.price = gammaflow::Price::from_raw(prices[seq % prices.size()]);

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

/// Print formatted latency statistics (cycles & converted ns).
static void print_stat(const char* label, std::uint64_t cycles, double tsc_to_ns) {
    double ns = cycles * tsc_to_ns;
    std::cout << "  " << std::left << std::setw(22) << label
              << std::right << std::setw(8) << cycles << " cycles  "
              << std::right << std::setw(8) << std::fixed << std::setprecision(0) << ns << " ns";
              
    if (ns < 1'000) {
        std::cout << "  (" << std::fixed << std::setprecision(0) << ns << " ns)";
    } else if (ns < 1'000'000) {
        std::cout << "  (" << std::fixed << std::setprecision(2) << (ns / 1'000.0) << " µs)";
    } else {
        std::cout << "  (" << std::fixed << std::setprecision(2) << (ns / 1'000'000.0) << " ms)";
    }
    std::cout << "\n";
}

// ═════════════════════════════════════════════════════════════════════════════
// Benchmark 1: Evaluator-only (single-threaded, no ring buffer)
// ═════════════════════════════════════════════════════════════════════════════

static void bench_evaluator_only(double tsc_to_ns) {
    std::cout << "── Benchmark 1: Evaluator-only (single-threaded, RDTSC) ──\n\n";

    gammaflow::RiskEvaluator evaluator;
    std::vector<std::uint64_t> latencies;
    latencies.reserve(NUM_EVENTS);

    std::vector<gammaflow::RiskEvent> events(NUM_EVENTS);
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        events[i] = make_event(i);
    }

    for (std::size_t i = 0; i < WARMUP_EVENTS && i < NUM_EVENTS; ++i) {
        volatile auto r = evaluator.evaluate(events[i]);
        (void)r;
    }

    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        std::uint64_t t0 = __rdtsc();
        volatile auto result = evaluator.evaluate(events[i]);
        std::uint64_t t1 = __rdtsc();
        (void)result;

        latencies.push_back(t1 - t0);
    }

    std::sort(latencies.begin(), latencies.end());

    std::uint64_t sum = 0;
    for (auto l : latencies) sum += l;

    auto percentile = [&](double p) -> std::uint64_t {
        auto idx = static_cast<std::size_t>(p * latencies.size());
        if (idx >= latencies.size()) idx = latencies.size() - 1;
        return latencies[idx];
    };

    print_stat("Average",      sum / latencies.size(), tsc_to_ns);
    print_stat("Median (p50)", percentile(0.50), tsc_to_ns);
    print_stat("p95",          percentile(0.95), tsc_to_ns);
    print_stat("p99",          percentile(0.99), tsc_to_ns);
    print_stat("p99.9",        percentile(0.999), tsc_to_ns);
    print_stat("Min",          latencies.front(), tsc_to_ns);
    print_stat("Max",          latencies.back(), tsc_to_ns);

    std::cout << "\n  Events evaluated: " << NUM_EVENTS << "\n\n";
}

// ═════════════════════════════════════════════════════════════════════════════
// Benchmark 2: End-to-end (producer → SPSC ring → evaluator, two threads)
// ═════════════════════════════════════════════════════════════════════════════

static void bench_end_to_end(double tsc_to_ns) {
    std::cout << "── Benchmark 2: End-to-end (Producer → cache-aligned ring → Evaluator) ──\n\n";

    // We pass PaddedEvent BY VALUE. At 64 bytes perfectly aligned, each enqueue
    // writes exactly 1 cache line, completely isolating adjacent events avoiding false sharing.
    // Heap-allocate to prevent stack overflow (64 bytes * 65536 = 4MB > 1MB Windows default stack).
    auto ring = std::make_unique<gammaflow::SPSCRingBuffer<PaddedEvent, RING_CAPACITY>>();
    gammaflow::RiskEvaluator evaluator;

    std::vector<std::uint64_t> latencies(NUM_EVENTS, 0);
    std::atomic<bool> consumer_done{false};

    std::vector<gammaflow::RiskEvent> events(NUM_EVENTS);
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        events[i] = make_event(i);
    }

#ifdef _WIN32
    // ── OS Memory Locking ──────────────────────────────────────────────────
    // Expand working set and pin hot arrays into physical RAM to prevent page faults.
    SIZE_T min_ws, max_ws;
    HANDLE hProcess = GetCurrentProcess();
    if (GetProcessWorkingSetSize(hProcess, &min_ws, &max_ws)) {
        SIZE_T needed = 128 * 1024 * 1024; // 128 MB
        if (min_ws < needed) {
            SetProcessWorkingSetSize(hProcess, needed, needed * 2);
        }
    }
    VirtualLock(ring.get(), sizeof(*ring));
    VirtualLock(latencies.data(), latencies.capacity() * sizeof(std::uint64_t));
    VirtualLock(events.data(), events.capacity() * sizeof(gammaflow::RiskEvent));

    // ── TLB & Cache Pre-Warming ─────────────────────────────────────────────
    // Walk the entire ring buffer once to force the OS to map all virtual pages
    // to physical pages, loading the TLB and preventing first-touch penalties.
    PaddedEvent dummy_ev{};
    for (std::size_t i = 0; i < ring->max_size(); ++i) {
        ring->try_push(dummy_ev);
    }
    for (std::size_t i = 0; i < ring->max_size(); ++i) {
        auto val = ring->try_pop();
        (void)val;
    }
#endif

    // ── Consumer thread ─────────────────────────────────────────────────
    std::thread consumer([&] {
#ifdef _WIN32
        SetThreadAffinityMask(GetCurrentThread(), 8); // Core 3
        SetThreadIdealProcessor(GetCurrentThread(), 3);
        SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_TIME_CRITICAL);
        SetThreadPriorityBoost(GetCurrentThread(), TRUE);
#endif

        std::size_t count = 0;
        while (count < NUM_EVENTS) {
            auto maybe = ring->try_pop();
            if (maybe.has_value()) {
                const PaddedEvent& p_ev = *maybe;

                // Evaluate.
                volatile auto result = evaluator.evaluate(p_ev.event);
                (void)result;

                // Measure latency immediately after evaluation is complete.
                std::uint64_t now_tsc = __rdtsc();

                if (count >= WARMUP_EVENTS) {
                    latencies[count] = now_tsc - p_ev.enqueue_tsc;
                }

                ++count;
            } else {
                _mm_pause(); // Hardware spin-wait
            }
        }
        consumer_done.store(true, std::memory_order_release);
    });

    // ── Producer (this thread) ──────────────────────────────────────────
#ifdef _WIN32
    SetThreadAffinityMask(GetCurrentThread(), 4); // Core 2
    SetThreadIdealProcessor(GetCurrentThread(), 2);
    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_TIME_CRITICAL);
    SetThreadPriorityBoost(GetCurrentThread(), TRUE);
#endif

    auto next_tick = Clock::now();
    for (std::size_t i = 0; i < NUM_EVENTS; ++i) {
        // Spin-wait 1µs to simulate a realistic network line rate (~1M msgs/sec)
        // and eliminate burst queueing delay.
        if (i > 0) {
            next_tick += std::chrono::microseconds(1);
            while (Clock::now() < next_tick) {
                _mm_pause(); // Hardware spin-wait
            }
        } else {
            next_tick = Clock::now();
        }

        PaddedEvent p_ev;
        p_ev.event = events[i];

        // Capture exactly before pushing
        p_ev.enqueue_tsc = __rdtsc();

        while (!ring->try_push(p_ev)) {
            _mm_pause(); // Hardware spin-wait, handling back-pressure
        }
    }

    consumer.join();

    // ── Statistics ───────────────────────────────────────────────────────
    auto valid_begin = latencies.begin() + WARMUP_EVENTS;
    auto valid_end = latencies.end();
    std::size_t valid_count = NUM_EVENTS - WARMUP_EVENTS;

    std::sort(valid_begin, valid_end);

    std::uint64_t sum = 0;
    for (auto it = valid_begin; it != valid_end; ++it) sum += *it;

    auto percentile = [&](double p) -> std::uint64_t {
        auto idx = static_cast<std::size_t>(p * valid_count);
        if (idx >= valid_count) idx = valid_count - 1;
        return *(valid_begin + idx);
    };

    print_stat("Average",      sum / valid_count, tsc_to_ns);
    print_stat("Median (p50)", percentile(0.50), tsc_to_ns);
    print_stat("p95",          percentile(0.95), tsc_to_ns);
    print_stat("p99",          percentile(0.99), tsc_to_ns);
    print_stat("p99.9",        percentile(0.999), tsc_to_ns);
    print_stat("Min",          *valid_begin, tsc_to_ns);
    print_stat("Max",          *(valid_end - 1), tsc_to_ns);

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
              << events_per_sec << " events/sec\n\n";
}

// ═════════════════════════════════════════════════════════════════════════════
// Main
// ═════════════════════════════════════════════════════════════════════════════

int main() {
#ifdef _WIN32
    SetPriorityClass(GetCurrentProcess(), REALTIME_PRIORITY_CLASS);
#endif

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

    std::cout << "  Calibrating RDTSC clock... ";
    double tsc_to_ns = get_tsc_to_ns_multiplier();
    std::cout << "Done! (1 cycle = " << std::fixed << std::setprecision(4) << tsc_to_ns << " ns)\n\n";

    bench_evaluator_only(tsc_to_ns);
    bench_end_to_end(tsc_to_ns);
    bench_throughput();

    std::cout << "══════════════════════════════════════════════════════════\n"
              << "  Benchmark complete.\n"
              << "══════════════════════════════════════════════════════════\n\n";

    return 0;
}
