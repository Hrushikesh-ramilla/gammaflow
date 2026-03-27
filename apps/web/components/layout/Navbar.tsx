"use client";

import React from "react";
import Link from "next/link";
import { useAuthStore } from "@/store/authStore";
import { ROUTES } from "@/lib/constants";
import { Button } from "../ui/Button";

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthStore();

  return (
    <nav className="navbar">
      <div className="navbar__container">
        <div className="navbar__left">
          <Link href={isAuthenticated ? ROUTES.dashboard : ROUTES.home} className="navbar__brand">
            <span className="navbar__logo">SYL</span>
          </Link>
        </div>

        <div className="navbar__right">
          {isAuthenticated ? (
            <>
              <span className="navbar__user">{user?.full_name || user?.email}</span>
              <Button variant="ghost" size="sm" onClick={logout}>
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Link href={ROUTES.login} className="navbar__link">
                Log in
              </Link>
              <Link href={ROUTES.register}>
                <Button variant="primary" size="sm">
                  Sign up
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
