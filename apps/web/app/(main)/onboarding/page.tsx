"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { UploadFlow } from "@/components/upload/UploadFlow";
import { ROUTES } from "@/lib/constants";
import { Button } from "@/components/ui/Button";

export default function OnboardingPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push(ROUTES.login);
    }
  }, [isAuthenticated, router]);

  const handleComplete = (syllabusId: string) => {
    router.push(ROUTES.study(syllabusId));
  };

  const skipOnboarding = () => {
    router.push(ROUTES.dashboard);
  };

  return (
    <div className="onboarding">
      <div className="onboarding-container">
        <h1 className="onboarding-title">Welcome to SYL!</h1>
        <p className="onboarding-subtitle">
          Let’s set up your first study domain. Upload your course syllabus to create your interactive knowledge graph.
        </p>
        
        <div className="onboarding-upload-card">
          <UploadFlow onComplete={handleComplete} />
        </div>

        <div className="onboarding-footer">
          <Button variant="ghost" onClick={skipOnboarding}>
            Skip for now, go to Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
