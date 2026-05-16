"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  ApiError,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
  startGoogleAuth,
} from "@/lib/api";
import type { AuthLoginDraft, AuthRegisterDraft, AuthUser } from "@/lib/types";

type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  user: AuthUser | null;
  status: AuthStatus;
  login: (draft: AuthLoginDraft) => Promise<AuthUser>;
  register: (draft: AuthRegisterDraft) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  startGoogleSignIn: (nextPath?: string) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const mountedRef = useRef(true);

  async function refresh() {
    try {
      const currentUser = await getCurrentUser();
      if (!mountedRef.current) return;
      setUser(currentUser);
      setStatus("authenticated");
    } catch (error) {
      if (!mountedRef.current) return;
      if (error instanceof ApiError && error.status === 401) {
        setUser(null);
        setStatus("anonymous");
        return;
      }
      setUser(null);
      setStatus("anonymous");
    }
  }

  useEffect(() => {
    mountedRef.current = true;
    void refresh();
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      async login(draft) {
        const nextUser = await loginUser(draft);
        setUser(nextUser);
        setStatus("authenticated");
        return nextUser;
      },
      async register(draft) {
        const nextUser = await registerUser(draft);
        setUser(nextUser);
        setStatus("authenticated");
        return nextUser;
      },
      async logout() {
        await logoutUser();
        setUser(null);
        setStatus("anonymous");
      },
      refresh,
      startGoogleSignIn(nextPath) {
        startGoogleAuth(nextPath);
      },
    }),
    [status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status !== "anonymous") return;
    router.replace(`/login?next=${encodeURIComponent(pathname || "/")}`);
  }, [pathname, router, status]);

  if (status === "loading") {
    return <AuthLoadingPanel label="Restoring your workspace" />;
  }
  if (status === "anonymous") {
    return null;
  }
  return <>{children}</>;
}

export function GuestOnly({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status !== "authenticated") return;
    const params = new URLSearchParams(window.location.search);
    const next = params.get("next") || "/";
    router.replace(next.startsWith("/") ? next : "/");
  }, [router, status]);

  if (status === "loading") {
    return <AuthLoadingPanel label="Checking your session" />;
  }
  if (status === "authenticated") {
    return null;
  }
  return <>{children}</>;
}

function AuthLoadingPanel({ label }: { label: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-6">
      <div className="w-full max-w-sm rounded-[28px] border border-line bg-panel p-6 shadow-soft">
        <div className="text-sm font-semibold text-ink">{label}</div>
        <div className="mt-2 text-sm text-muted">Preparing authentication state.</div>
      </div>
    </div>
  );
}
