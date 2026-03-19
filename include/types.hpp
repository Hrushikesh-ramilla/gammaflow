#pragma once

// ─────────────────────────────────────────────────────────────────────────────
// GammaFlow — types.hpp
// Fixed-point numeric types for deterministic, floating-point-free arithmetic.
// ─────────────────────────────────────────────────────────────────────────────

#include <cstdint>
#include <compare>
#include <ostream>
#include <string>
#include <stdexcept>
#include <type_traits>

namespace gammaflow {

/// Compile-time scaling factor: 10^Precision.
/// Default precision of 8 decimal places covers sub-cent financial granularity.
template <int Precision = 8>
class FixedPoint {
    static_assert(Precision > 0 && Precision <= 18,
                  "Precision must be in [1, 18] to fit within int64_t");

public:
    /// The underlying integral representation.
    using raw_type = std::int64_t;

    /// Number of implied decimal digits.
    static constexpr int precision = Precision;

    /// The scaling factor (10^Precision), computed at compile time.
    static constexpr raw_type scale = []() constexpr {
        raw_type s = 1;
        for (int i = 0; i < Precision; ++i) s *= 10;
        return s;
    }();

    // ── Constructors ────────────────────────────────────────────────────────

    /// Default-construct to zero.
    constexpr FixedPoint() noexcept : raw_{0} {}

    /// Construct from an integer value (no fractional part).
    constexpr explicit FixedPoint(std::int64_t integer) noexcept
        : raw_{integer * scale} {}

    /// Construct from integer + fractional parts.
    /// Example: FixedPoint(123, 45000000) with Precision=8 represents 123.45.
    constexpr FixedPoint(std::int64_t integer, std::int64_t frac) noexcept
        : raw_{integer * scale + frac} {}

    /// Named constructor from the raw underlying value.
    [[nodiscard]] static constexpr FixedPoint from_raw(raw_type raw) noexcept {
        FixedPoint fp;
        fp.raw_ = raw;
        return fp;
    }

    // ── Accessors ───────────────────────────────────────────────────────────

    [[nodiscard]] constexpr raw_type raw() const noexcept { return raw_; }

    /// Integer portion (truncated toward zero).
    [[nodiscard]] constexpr std::int64_t integer_part() const noexcept {
        return raw_ / scale;
    }

    /// Fractional portion as a scaled integer.
    [[nodiscard]] constexpr std::int64_t fractional_part() const noexcept {
        return raw_ % scale;
    }

    // ── Arithmetic Operators ────────────────────────────────────────────────

    constexpr FixedPoint operator+(FixedPoint rhs) const noexcept {
        return from_raw(raw_ + rhs.raw_);
    }

    constexpr FixedPoint operator-(FixedPoint rhs) const noexcept {
        return from_raw(raw_ - rhs.raw_);
    }

    /// Multiplication: (a * b) / scale — uses __int128 to avoid overflow.
    constexpr FixedPoint operator*(FixedPoint rhs) const noexcept {
        auto wide = static_cast<__int128>(raw_) * rhs.raw_;
        return from_raw(static_cast<raw_type>(wide / scale));
    }

    /// Division: (a * scale) / b — uses __int128 to avoid overflow.
    constexpr FixedPoint operator/(FixedPoint rhs) const {
        if (rhs.raw_ == 0) {
            throw std::domain_error("FixedPoint: division by zero");
        }
        auto wide = static_cast<__int128>(raw_) * scale;
        return from_raw(static_cast<raw_type>(wide / rhs.raw_));
    }

    constexpr FixedPoint& operator+=(FixedPoint rhs) noexcept {
        raw_ += rhs.raw_; return *this;
    }

    constexpr FixedPoint& operator-=(FixedPoint rhs) noexcept {
        raw_ -= rhs.raw_; return *this;
    }

    constexpr FixedPoint operator-() const noexcept {
        return from_raw(-raw_);
    }

    // ── Comparison (C++20 three-way) ────────────────────────────────────────

    constexpr auto operator<=>(const FixedPoint&) const noexcept = default;

    // ── String Conversion ───────────────────────────────────────────────────

    [[nodiscard]] std::string to_string() const {
        auto int_part = integer_part();
        auto frac_part = fractional_part();
        if (frac_part < 0) frac_part = -frac_part;

        std::string frac_str = std::to_string(frac_part);
        // Pad with leading zeros to match precision width.
        while (static_cast<int>(frac_str.size()) < Precision) {
            frac_str = "0" + frac_str;
        }

        std::string sign = (raw_ < 0 && int_part == 0) ? "-" : "";
        return sign + std::to_string(int_part) + "." + frac_str;
    }

    friend std::ostream& operator<<(std::ostream& os, const FixedPoint& fp) {
        return os << fp.to_string();
    }

private:
    raw_type raw_;
};

// ── Convenient Aliases ──────────────────────────────────────────────────────

/// Price type — 8 decimal places (sub-cent granularity).
using Price    = FixedPoint<8>;

/// Quantity type — 4 decimal places (fractional share support).
using Quantity = FixedPoint<4>;

} // namespace gammaflow
