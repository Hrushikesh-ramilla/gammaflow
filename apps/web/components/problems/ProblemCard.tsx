"use client";

import React from "react";
import type { Problem } from "@/lib/types";
import { TierBadge } from "./TierBadge";
import { usePDFStore } from "@/store/pdf-store";

interface ProblemCardProps {
  problem: Problem;
  onStatusChange?: (problemId: string, status: Problem["user_status"]) => void;
}

const STATUS_CYCLE: Problem["user_status"][] = ["todo", "in_progress", "done"];
const STATUS_LABELS: Record<Problem["user_status"], string> = {
  todo: "To Do",
  in_progress: "In Progress",
  done: "Done ✓",
};

export function ProblemCard({ problem, onStatusChange }: ProblemCardProps) {
  const { jumpToPage } = usePDFStore();

  const handlePageClick = () => {
    jumpToPage(problem.page_number);
  };

  const cycleStatus = () => {
    const idx = STATUS_CYCLE.indexOf(problem.user_status);
    const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
    onStatusChange?.(problem.id, next);
  };

  const isLong = problem.problem_text.length > 200;

  return (
    <div
      className={`problem-card problem-card--${problem.user_status}`}
      data-tier={problem.rank_tier}
    >
      {/* Header */}
      <div className="problem-card__header">
        <div className="problem-card__meta">
          {problem.problem_number && (
            <span className="problem-number">#{problem.problem_number}</span>
          )}
          <TierBadge tier={problem.rank_tier} size="sm" />
        </div>
        <button
          className={`problem-status-btn problem-status-btn--${problem.user_status}`}
          onClick={cycleStatus}
          aria-label={`Status: ${STATUS_LABELS[problem.user_status]}`}
        >
          {STATUS_LABELS[problem.user_status]}
        </button>
      </div>

      {/* Problem text */}
      <p className={`problem-text ${isLong ? "problem-text--truncated" : ""}`}>
        {problem.problem_text}
      </p>

      {/* Footer */}
      <div className="problem-card__footer">
        {problem.chapter && (
          <span className="problem-chapter">{problem.chapter}</span>
        )}
        <button
          className="problem-page-link"
          onClick={handlePageClick}
          aria-label={`Jump to page ${problem.page_number}`}
        >
          p.{problem.page_number} →
        </button>
      </div>
    </div>
  );
}
