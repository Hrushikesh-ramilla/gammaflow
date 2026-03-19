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

        // ── 1. Price component ──────────────────────────────────────────────

        std::int32_t price_score = 0;

        if (event.price < penny_threshold) {
            // Sub-dollar instruments are inherently volatile.
            price_score = 400;
        } else if (event.price < low_price) {
            // Low-priced equities — elevated risk.
            price_score = 300;
        } else if (event.price < mid_price) {
            // Mid-range — moderate risk.
            price_score = 150;
        } else if (event.price < high_price) {
            // Blue-chip territory — lower risk.
            price_score = 50;
        } else {
            // Ultra-high-priced instruments (e.g. BRK.A) — minimal base risk.
            price_score = 20;
        }

        // ── 2. Quantity component ───────────────────────────────────────────

        std::int32_t qty_score = 0;

        if (event.quantity < tiny_qty) {
            // Retail-size order — negligible market impact.
            qty_score = 10;
        } else if (event.quantity < small_qty) {
            // Small block — low impact.
            qty_score = 50;
        } else if (event.quantity < large_qty) {
            // Institutional block — moderate impact.
            qty_score = 200;
        } else if (event.quantity < huge_qty) {
            // Large block — significant market impact.
            qty_score = 350;
        } else {
            // Massive order — potential market-moving event.
            qty_score = 500;
        }

        // ── 3. Cross-factor amplification (fuzzy AND rules) ─────────────────

        std::int32_t penalty = 0;

        // Rule A: penny stock + large quantity → pump-and-dump signal.
        if (event.price < penny_threshold && event.quantity >= large_qty) {
            penalty += 200;
        }

        // Rule B: high-value instrument + huge quantity → whale activity.
        if (event.price >= high_price && event.quantity >= huge_qty) {
            penalty += 150;
        }

        // Rule C: any extremely large order gets a flat penalty.
        if (event.quantity >= huge_qty) {
            penalty += 50;
        }

        // ── 4. Combine & clamp ──────────────────────────────────────────────

        std::int32_t raw_score = price_score + qty_score + penalty;

        // Clamp to [0, 1000] using branchless min/max via ternary.
        std::int32_t score = raw_score < 0    ? 0
                           : raw_score > 1000 ? 1000
                           :                    raw_score;

        // ── 5. Derive tier ──────────────────────────────────────────────────

        RiskTier tier;
        if (score >= 750)      tier = RiskTier::CRITICAL;
        else if (score >= 500) tier = RiskTier::HIGH;
        else if (score >= 250) tier = RiskTier::MEDIUM;
        else                   tier = RiskTier::LOW;

        return RiskResult{event.id, score, tier};
    }
};

} // namespace gammaflow
