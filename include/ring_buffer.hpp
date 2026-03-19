#pragma once

// ─────────────────────────────────────────────────────────────────────────────
// GammaFlow — ring_buffer.hpp
// Lock-free Single-Producer Single-Consumer (SPSC) ring buffer.
//
// Design rationale:
//   - Exactly one writer thread and one reader thread operate concurrently.
//   - Memory ordering uses acquire/release semantics on the head (consumer)
//     and tail (producer) indices — no sequentially-consistent fences, no
//     mutexes, and no OS-level synchronization primitives.
//   - The buffer capacity is always a power of two so that modular indexing
//     reduces to a bitwise AND, avoiding expensive integer division.
//   - Head and tail are placed on separate cache lines to eliminate false
//     sharing between the producer and consumer cores.
// ─────────────────────────────────────────────────────────────────────────────

#include <atomic>
#include <array>
#include <cassert>
#include <cstddef>
#include <optional>
#include <type_traits>

namespace gammaflow {

// ─────────────────────────────────────────────────────────────────────────────
// SPSCRingBuffer<T, Capacity>
//
// Template parameters:
//   T        — element type (typically a pointer or trivially copyable struct).
//   Capacity — must be a power of two.  The usable capacity is (Capacity - 1)
//              because one slot is always left empty to distinguish full from
//              empty state.
// ─────────────────────────────────────────────────────────────────────────────

template <typename T, std::size_t Capacity>
class SPSCRingBuffer {
    static_assert(Capacity > 1,
                  "Capacity must be > 1");
    static_assert((Capacity & (Capacity - 1)) == 0,
                  "Capacity must be a power of two for fast modular indexing");

public:
    // ── Construction ────────────────────────────────────────────────────────

    SPSCRingBuffer() noexcept
        : head_{0}
        , tail_{0}
        , buffer_{} {}

    // Non-copyable, non-movable.
    SPSCRingBuffer(const SPSCRingBuffer&)            = delete;
    SPSCRingBuffer& operator=(const SPSCRingBuffer&) = delete;
    SPSCRingBuffer(SPSCRingBuffer&&)                 = delete;
    SPSCRingBuffer& operator=(SPSCRingBuffer&&)      = delete;

    // ── Producer API (single writer thread only) ────────────────────────────

    /// Try to enqueue an element.  Returns true on success, false if full.
    ///
    /// Memory ordering:
    ///   - tail_ is written with RELEASE so the consumer sees the stored
    ///     element when it reads tail_ with ACQUIRE.
    ///   - head_ is read with ACQUIRE so the producer sees the consumer's
    ///     latest progress.
    bool try_push(const T& item) noexcept {
        const std::size_t current_tail = tail_.load(std::memory_order_relaxed);
        const std::size_t next_tail    = increment(current_tail);

        // If next_tail == head_, the buffer is full (one empty slot sentinel).
        if (next_tail == head_.load(std::memory_order_acquire)) {
            return false;
        }

        buffer_[current_tail] = item;

        // Publish the new tail — the consumer may now see this element.
        tail_.store(next_tail, std::memory_order_release);
        return true;
    }

    // ── Consumer API (single reader thread only) ────────────────────────────

    /// Try to dequeue an element.  Returns std::nullopt if empty.
    ///
    /// Memory ordering:
    ///   - head_ is written with RELEASE so the producer sees the freed slot
    ///     when it reads head_ with ACQUIRE.
    ///   - tail_ is read with ACQUIRE so the consumer sees the producer's
    ///     latest writes to buffer_.
    [[nodiscard]] std::optional<T> try_pop() noexcept {
        const std::size_t current_head = head_.load(std::memory_order_relaxed);

        // If head_ == tail_, the buffer is empty.
        if (current_head == tail_.load(std::memory_order_acquire)) {
            return std::nullopt;
        }

        T item = buffer_[current_head];

        // Advance head — the producer may now reuse this slot.
        head_.store(increment(current_head), std::memory_order_release);
        return item;
    }

    // ── Introspection ───────────────────────────────────────────────────────

    /// Approximate number of elements currently in the buffer.
    /// Safe to call from any thread, but the value may be stale.
    [[nodiscard]] std::size_t size_approx() const noexcept {
        const std::size_t h = head_.load(std::memory_order_acquire);
        const std::size_t t = tail_.load(std::memory_order_acquire);
        return (t - h) & mask_;
    }

    /// Returns true if the buffer appears empty (snapshot, may be stale).
    [[nodiscard]] bool empty() const noexcept {
        return head_.load(std::memory_order_acquire)
            == tail_.load(std::memory_order_acquire);
    }

    /// Compile-time capacity (including the sentinel slot).
    [[nodiscard]] static constexpr std::size_t capacity() noexcept {
        return Capacity;
    }

    /// Maximum number of elements that can be stored simultaneously.
    [[nodiscard]] static constexpr std::size_t max_size() noexcept {
        return Capacity - 1;
    }

private:
    // ── Helpers ─────────────────────────────────────────────────────────────

    static constexpr std::size_t mask_ = Capacity - 1;

    /// Advance an index by one, wrapping via bitmask (branchless).
    [[nodiscard]] static constexpr std::size_t increment(std::size_t idx) noexcept {
        return (idx + 1) & mask_;
    }

    // ── Data ────────────────────────────────────────────────────────────────
    // head_ and tail_ are on separate cache lines to avoid false sharing
    // between the producer (writes tail_) and consumer (writes head_).

    /// Consumer index — only the reader thread writes this.
    alignas(64) std::atomic<std::size_t> head_;

    /// Producer index — only the writer thread writes this.
    alignas(64) std::atomic<std::size_t> tail_;

    /// The underlying fixed-size storage.
    std::array<T, Capacity> buffer_;
};

} // namespace gammaflow
