// pattern: Imperative Shell
"use client";

import { useCallback, useState } from "react";

const AUTH_KEY = "docquery.auth";

type AuthState = {
  isLoggedIn: boolean;
  username: string;
};

const DEFAULT_STATE: AuthState = { isLoggedIn: false, username: "" };

export function useAuthStub() {
  const [auth, setAuth] = useState<AuthState>(() => {
    if (typeof window === "undefined") return DEFAULT_STATE;
    try {
      const stored = localStorage.getItem(AUTH_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as AuthState;
        if (parsed?.isLoggedIn) return parsed;
      }
    } catch {
      // Corrupt or missing storage keeps the user logged out.
    }
    return DEFAULT_STATE;
  });

  const login = useCallback((username: string) => {
    const next: AuthState = { isLoggedIn: true, username };
    setAuth(next);
    try {
      localStorage.setItem(AUTH_KEY, JSON.stringify(next));
    } catch {
      // Storage failure should not block demo login.
    }
  }, []);

  const logout = useCallback(() => {
    setAuth(DEFAULT_STATE);
    try {
      localStorage.removeItem(AUTH_KEY);
    } catch {
      // Ignore storage errors on logout.
    }
  }, []);

  return { isLoggedIn: auth.isLoggedIn, username: auth.username, login, logout };
}
