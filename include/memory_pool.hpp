#pragma once

// ─────────────────────────────────────────────────────────────────────────────
// GammaFlow — memory_pool.hpp
// Lock-free, cache-aligned object pool with O(1) allocate / deallocate.
//
// Design rationale:
//   - Pre-allocates a fixed array of T objects to eliminate runtime heap calls.
//   - Uses a lock-free free-list (Treiber stack) built from atomic CAS so
//     multiple threads can allocate/deallocate concurrently without mutexes.
//   - Each slot is aligned to a 64-byte cache line to prevent false sharing
//     when adjacent slots are accessed by different CPU cores.
// ─────────────────────────────────────────────────────────────────────────────

#include <atomic>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <new>
#include <type_traits>

namespace gammaflow {

/// Sentinel value indicating the end of the free-list chain.
inline constexpr std::uint32_t POOL_NULL = UINT32_MAX;

// ─────────────────────────────────────────────────────────────────────────────
// ObjectPool<T, Capacity>
//
// Template parameters:
//   T        — the object type stored in the pool (must be trivially
//              destructible so we can skip per-object cleanup).
//   Capacity — maximum number of live objects the pool can provide.
//
// Memory layout:
//   slots_[i] is aligned to a 64-byte boundary so that two slots accessed
//   by different threads will never share a cache line.
// ─────────────────────────────────────────────────────────────────────────────

template <typename T, std::size_t Capacity>
class ObjectPool {
    static_assert(Capacity > 0, "ObjectPool capacity must be > 0");
    static_assert(Capacity < POOL_NULL,
                  "Capacity must be < UINT32_MAX (reserved as sentinel)");

public:
    // ── Construction ────────────────────────────────────────────────────────

    ObjectPool() noexcept {
        // Build the initial free-list: slot 0 → 1 → 2 → … → POOL_NULL.
        for (std::uint32_t i = 0; i < Capacity - 1; ++i) {
            slots_[i].next.store(i + 1, std::memory_order_relaxed);
        }
        slots_[Capacity - 1].next.store(POOL_NULL, std::memory_order_relaxed);

        head_.store(0, std::memory_order_release);
    }

    // Non-copyable, non-movable (the pool owns a fixed block of memory).
    ObjectPool(const ObjectPool&)            = delete;
    ObjectPool& operator=(const ObjectPool&) = delete;
    ObjectPool(ObjectPool&&)                 = delete;
    ObjectPool& operator=(ObjectPool&&)      = delete;

    // ── Allocate ────────────────────────────────────────────────────────────

    /// Pop the head of the free-list and return a pointer to the raw storage.
    /// Returns nullptr if the pool is exhausted.
    /// Complexity: O(1) amortised (single CAS loop).
    [[nodiscard]] T* allocate() noexcept {
        std::uint32_t old_head = head_.load(std::memory_order_acquire);

        while (old_head != POOL_NULL) {
            std::uint32_t new_head =
                slots_[old_head].next.load(std::memory_order_relaxed);

            if (head_.compare_exchange_weak(old_head, new_head,
                                            std::memory_order_acq_rel,
                                            std::memory_order_acquire)) {
                return object_ptr(old_head);
            }
            // CAS failed — old_head has been refreshed by compare_exchange_weak.
        }

        return nullptr; // Pool exhausted.
    }

    // ── Deallocate ──────────────────────────────────────────────────────────

    /// Push the slot back onto the free-list head.
    /// The caller must ensure `ptr` was obtained from this pool.
    void deallocate(T* ptr) noexcept {
        assert(ptr != nullptr);
        std::uint32_t index = slot_index(ptr);
        assert(index < Capacity);

        std::uint32_t old_head = head_.load(std::memory_order_acquire);
        do {
            slots_[index].next.store(old_head, std::memory_order_relaxed);
        } while (!head_.compare_exchange_weak(old_head, index,
                                              std::memory_order_acq_rel,
                                              std::memory_order_acquire));
    }

    // ── Introspection ───────────────────────────────────────────────────────

    /// Returns the compile-time capacity of the pool.
    [[nodiscard]] static constexpr std::size_t capacity() noexcept {
        return Capacity;
    }

    /// Returns a pointer to the beginning of the backing storage (for tests).
    [[nodiscard]] const void* storage_base() const noexcept {
        return &slots_[0];
    }

private:
    // ── Slot ────────────────────────────────────────────────────────────────
    // Each slot is aligned to a hardware cache line (64 bytes) and holds:
    //   • Raw storage large enough for one T object.
    //   • An atomic next-index for the lock-free free-list.
    // The padding ensures no two slots ever share a cache line.

    struct alignas(64) Slot {
        /// Raw uninitialized storage for one T.
        alignas(alignof(T)) unsigned char storage[sizeof(T)];

        /// Free-list link (index of the next free slot, or POOL_NULL).
        std::atomic<std::uint32_t> next{POOL_NULL};
    };

    static_assert(sizeof(Slot) % 64 == 0,
                  "Slot must be a multiple of 64 bytes (cache-line aligned)");

    // ── Helpers ─────────────────────────────────────────────────────────────

    /// Interpret the raw storage of slot `i` as a T*.
    [[nodiscard]] T* object_ptr(std::uint32_t i) noexcept {
        return std::launder(reinterpret_cast<T*>(slots_[i].storage));
    }

    /// Reverse-map a T* back to its slot index.
    [[nodiscard]] std::uint32_t slot_index(const T* ptr) const noexcept {
        auto byte_ptr  = reinterpret_cast<const unsigned char*>(ptr);
        auto base_ptr  = reinterpret_cast<const unsigned char*>(&slots_[0]);
        return static_cast<std::uint32_t>(
            (byte_ptr - base_ptr) / sizeof(Slot));
    }

    // ── Data ────────────────────────────────────────────────────────────────

    /// The slot array — all memory is allocated here (stack or static).
    std::array<Slot, Capacity> slots_;

    /// Head of the lock-free free-list (Treiber stack).
    alignas(64) std::atomic<std::uint32_t> head_{0};
};

} // namespace gammaflow
