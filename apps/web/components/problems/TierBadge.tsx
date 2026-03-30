"use client";

import React from "react";
import type { ProblemTier } from "@/lib/types";
import { TIER_LABELS } from "@/lib/constants";

interface TierBadgeProps {
  tier: ProblemTier | null;
  size?: "sm" | "md";
}

const TIER_STYLES: Record<ProblemTier, string> = {
  EXAM_LIKELY: "tier-badge--exam",
  GOOD_PRACTICE: "tier-badge--practice",
  OPTIONAL: "tier-badge--optional",
};

export function TierBadge({ tier, size = "md" }: TierBadgeProps) {
  if (!tier) return null;

  return (
    <span
      className={`tier-badge tier-badge--${size} ${TIER_STYLES[tier]}`}
      title={TIER_LABELS[tier]}
    >
      {TIER_LABELS[tier]}
    </span>
  );
}
