"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { ROUTES, PUBLIC_ROUTES } from "@/lib/constants";

export function useAuth() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, login, register, logout, init } = useAuthStore();
  const [isReady, setIsReady] = useState(false);

  // Initialize auth state on mount (e.g. check localStorage/cookies)
  useEffect(() => {
    init().finally(() => setIsReady(true));
  }, [init]);

  // Route protection guard
  useEffect(() => {
    if (!isReady) return;

    const isPublicRoute = PUBLIC_ROUTES.some(route => pathname?.startsWith(route));
    const isAuthRoute = pathname === ROUTES.login || pathname === ROUTES.register;

    if (!isAuthenticated && !isPublicRoute) {
      // Redirect to login if unauthenticated user tries to access protected route
      router.push(`${ROUTES.login}?returnUrl=${encodeURIComponent(pathname || "")}`);
    } else if (isAuthenticated && isAuthRoute) {
      // Redirect to dashboard if authenticated user tries to access login/register
      router.push(ROUTES.dashboard);
    }
  }, [isAuthenticated, isReady, pathname, router]);

  return {
    user,
    isAuthenticated,
    isLoading: isLoading || !isReady,
    login,
    register,
    logout,
  };
}
