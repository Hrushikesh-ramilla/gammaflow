#pragma once

// ─────────────────────────────────────────────────────────────────────────────
// GammaFlow — evaluator.hpp
// Zero-allocation fuzzy-rule risk evaluator.
//
// Design rationale:
//   - All arithmetic uses FixedPoint — no floating-point instructions at all.
//   - The decision tree is fully branchless where possible; remaining branches
//     are structured as a flat if/else chain for branch-predictor friendliness.
//   - No heap allocation, no virtual dispatch, no exceptions on the hot path.
//   - Risk score is returned as a raw int32 in [0, 1000] — higher means
//     riskier.  Downstream systems can map this to tiers (LOW / MED / HIGH /
//     CRITICAL) without additional computation.
// ─────────────────────────────────────────────────────────────────────────────

#include "types.hpp"
#include "models.hpp"

#include <cstdint>

namespace gammaflow {

/// Risk tiers for human-readable classification.
enum class RiskTier : std::uint8_t {
    LOW      = 0,   //   0 – 249
    MEDIUM   = 1,   // 250 – 499
    HIGH     = 2,   // 500 – 749
    CRITICAL = 3,   // 750 – 1000
};

/// Result of a single risk evaluation — tightly packed, trivially copyable.
#pragma pack(push, 1)
struct RiskResult {
    std::uint64_t event_id;     // Correlates back to the source RiskEvent.
    std::int32_t  score;        // [0, 1000] — higher ⟹ riskier.
    RiskTier      tier;         // Derived classification.
};
#pragma pack(pop)

// ─────────────────────────────────────────────────────────────────────────────
// RiskEvaluator
//
// Stateless, thread-safe evaluator.  All thresholds are compile-time
// constants expressed in FixedPoint, so the optimizer can inline them as
// immediate operands — no memory loads required.
// ─────────────────────────────────────────────────────────────────────────────

class RiskEvaluator {
public:
    // ── Compile-time threshold constants ────────────────────────────────────
    // All values use FixedPoint::from_raw() so there is zero runtime cost.

    // ── Price thresholds (8 decimal places) ─────────────────────────────────
    //   penny_threshold  =    1.00
    //   low_price        =   10.00
    //   mid_price        =  100.00
    //   high_price       = 1000.00

    static constexpr Price penny_threshold = Price::from_raw(1'00000000LL);
    static constexpr Price low_price       = Price::from_raw(10'00000000LL);
    static constexpr Price mid_price       = Price::from_raw(100'00000000LL);
    static constexpr Price high_price      = Price::from_raw(1000'00000000LL);

    // ── Quantity thresholds (4 decimal places) ──────────────────────────────
    //   tiny_qty   =      10
    //   small_qty  =     100
    //   large_qty  =   10000
    //   huge_qty   =  100000

    static constexpr Quantity tiny_qty  = Quantity::from_raw(10'0000LL);
    static constexpr Quantity small_qty = Quantity::from_raw(100'0000LL);
    static constexpr Quantity large_qty = Quantity::from_raw(10000'0000LL);
    static constexpr Quantity huge_qty  = Quantity::from_raw(100000'0000LL);

    // ── Scoring weights (applied via integer multiply + shift) ──────────────
    // Using bit shifts instead of division keeps the hot path free of
    // expensive idiv instructions.

    static constexpr std::int32_t WEIGHT_PRICE_COMPONENT = 5;   // × 2^5 = 32
    static constexpr std::int32_t WEIGHT_QTY_COMPONENT   = 4;   // × 2^4 = 16

    // ── Core evaluation ─────────────────────────────────────────────────────

    /// Evaluate a single RiskEvent.  Returns a RiskResult with no heap
    /// allocation and no floating-point arithmetic.
    ///
    /// Fuzzy-rule logic:
    ///   1. Compute a price_score in [0, 500] based on price tier.
    ///   2. Compute a qty_score   in [0, 500] based on quantity tier.
    ///   3. Combine: raw = price_score + qty_score, clamped to [0, 1000].
    ///   4. Apply cross-factor penalties:
    ///        – Penny stock + large quantity → amplified risk.
    ///        – High-value instrument + huge quantity → amplified risk.
    [[nodiscard]] RiskResult evaluate(const RiskEvent& event) const noexcept {

        // ── 0. Structural logic (Predictable Branches) ──────────────────────
        // The CPU branch predictor easily handles these baseline structural checks.
        if (event.quantity.raw() <= 0 || event.price.raw() <= 0) {
            return RiskResult{event.id, 0, RiskTier::LOW};
        }

        // ── 1. Price component (Branchless) ─────────────────────────────────
        std::int32_t price_score = 
              (event.price < penny_threshold) * 400
            + (event.price >= penny_threshold && event.price < low_price) * 300
            + (event.price >= low_price && event.price < mid_price) * 150
            + (event.price >= mid_price && event.price < high_price) * 50
            + (event.price >= high_price) * 20;

        // ── 2. Quantity component (Branchless) ──────────────────────────────
        std::int32_t qty_score = 
              (event.quantity < tiny_qty) * 10
            + (event.quantity >= tiny_qty && event.quantity < small_qty) * 50
            + (event.quantity >= small_qty && event.quantity < large_qty) * 200
            + (event.quantity >= large_qty && event.quantity < huge_qty) * 350
            + (event.quantity >= huge_qty) * 500;

        // ── 3. Cross-factor amplification (Branchless) ──────────────────────
        std::int32_t penalty = 
              (event.price < penny_threshold && event.quantity >= large_qty) * 200
            + (event.price >= high_price && event.quantity >= huge_qty) * 150
            + (event.quantity >= huge_qty) * 50;

        // ── 4. Combine & clamp (Predictable Branches) ───────────────────────
        std::int32_t score = price_score + qty_score + penalty;
        
        if (score > 1000) {
            score = 1000;
        } else if (score < 0) {
            score = 0;
        }

        // ── 5. Derive tier (Predictable Branches) ───────────────────────────
        RiskTier tier;
        if (score >= 750)      tier = RiskTier::CRITICAL;
        else if (score >= 500) tier = RiskTier::HIGH;
        else if (score >= 250) tier = RiskTier::MEDIUM;
        else                   tier = RiskTier::LOW;

        return RiskResult{event.id, score, tier};
    }
};

} // namespace gammaflow
