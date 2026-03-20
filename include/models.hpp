#pragma once

// ─────────────────────────────────────────────────────────────────────────────
// GammaFlow — models.hpp
// Core data models for the risk analytics pipeline.
// ─────────────────────────────────────────────────────────────────────────────

#include "types.hpp"

#include <cstdint>
#include <array>
#include <chrono>
#include <string_view>

namespace gammaflow {

/// Nanosecond-precision timestamp for event ordering.
using Timestamp = std::chrono::time_point<std::chrono::steady_clock>;

/// Fixed-size instrument identifier (8 bytes, null-padded).
/// Using a fixed array avoids heap allocation and keeps the struct trivially
/// copyable for zero-cost serialization into shared memory / ring buffers.
using InstrumentId = std::array<char, 8>;

// ─────────────────────────────────────────────────────────────────────────────
// RiskEvent
//
// Represents a single market event flowing through the risk pipeline.
// The struct is tightly packed (#pragma pack) to eliminate padding bytes,
// ensuring deterministic memory layout for:
//   - Binary serialization without an encoding layer
//   - Cache-line-friendly batching
//   - Memory-mapped I/O and IPC ring buffers
// ─────────────────────────────────────────────────────────────────────────────

struct RiskEvent {
    /// Monotonically increasing event identifier.
    std::uint64_t id;

    /// Nanosecond-resolution event timestamp (epoch-relative).
    /// Stored as raw nanoseconds rather than chrono::time_point to guarantee
    /// a trivial, packed memory layout.
    std::int64_t timestamp_ns;

    /// Instrument symbol, e.g. "AAPL", "TSLA". Null-padded to 8 bytes.
    InstrumentId instrument;

    /// Trade / quote price in fixed-point representation (8 decimal places).
    Price price;

    /// Trade / quote quantity in fixed-point representation (4 decimal places).
    Quantity quantity;
};

// Compile-time layout assertions — fail fast if assumptions break.
static_assert(sizeof(RiskEvent) ==
    sizeof(std::uint64_t)   +   // id              — 8
    sizeof(std::int64_t)    +   // timestamp_ns    — 8
    sizeof(InstrumentId)    +   // instrument      — 8
    sizeof(Price)           +   // price           — 8
    sizeof(Quantity),           // quantity         — 8
    "RiskEvent must be tightly packed with no padding"
);

static_assert(std::is_trivially_copyable_v<RiskEvent>,
              "RiskEvent must be trivially copyable for zero-copy I/O");

} // namespace gammaflow
