"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { syllabuses as syllabusApi } from "@/lib/api";
import { UploadFlow } from "@/components/upload/UploadFlow";
import type { Syllabus } from "@/lib/types";
import { ROUTES } from "@/lib/constants";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuthStore();
  const [syllabuses, setSyllabuses] = useState<Syllabus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push(ROUTES.login);
      return;
    }
    syllabusApi
      .list()
      .then(setSyllabuses)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [isAuthenticated, router]);

  const handleStudy = (syllabusId: string) => {
    router.push(ROUTES.study(syllabusId));
  };

  return (
    <div className="dashboard">
      {/* Navbar */}
      <header className="dashboard-nav">
        <span className="dashboard-brand">SYL</span>
        <div className="dashboard-nav-actions">
          <span className="dashboard-user">{user?.full_name || user?.email}</span>
          <button
            id="dashboard-logout-btn"
            className="btn btn--ghost btn--sm"
            onClick={logout}
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        {/* Hero section */}
        <section className="dashboard-hero">
          <h1 className="dashboard-title">Your study sessions</h1>
          <p className="dashboard-subtitle">
            Upload a syllabus to get started — your AI study partner will map your materials and guide you through every topic.
          </p>
          <button
            id="dashboard-new-btn"
            className="btn btn--primary"
            onClick={() => setShowUpload(true)}
          >
            + New syllabus
          </button>
        </section>

        {/* Upload modal */}
        {showUpload && (
          <div className="modal-overlay" onClick={() => setShowUpload(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <button
                className="modal-close"
                onClick={() => setShowUpload(false)}
                aria-label="Close upload"
              >
                ✕
              </button>
              <UploadFlow
                onComplete={(syllabusId) => {
                  setShowUpload(false);
                  router.push(ROUTES.study(syllabusId));
                }}
              />
            </div>
          </div>
        )}

        {/* Syllabus grid */}
        {isLoading ? (
          <div className="dashboard-loading">Loading your syllabuses…</div>
        ) : syllabuses.length === 0 ? (
          <div className="dashboard-empty">
            <div className="dashboard-empty-icon">📚</div>
            <h2 className="dashboard-empty-title">No syllabuses yet</h2>
            <p className="dashboard-empty-text">
              Upload your first syllabus PDF to get started.
            </p>
          </div>
        ) : (
          <div className="syllabus-grid">
            {syllabuses.map((s) => (
              <div key={s.id} className="syllabus-card">
                <div className="syllabus-card__icon">📘</div>
                <div className="syllabus-card__body">
                  <h3 className="syllabus-card__name">{s.course_name}</h3>
                  <p className="syllabus-card__meta">
                    {s.topic_count} topics · Created{" "}
                    {new Date(s.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  className="btn btn--primary btn--sm"
                  onClick={() => handleStudy(s.id)}
                >
                  Study →
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
