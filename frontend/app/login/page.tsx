"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GuestOnly, useAuth } from "@/components/auth-provider";
import { AuthShell } from "@/components/auth-shell";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login, startGoogleSignIn } = useAuth();
  const router = useRouter();
  const [nextPath, setNextPath] = useState("/");
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get("next");
    if (value && value.startsWith("/")) {
      setNextPath(value);
    }
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await login(form);
      router.replace(nextPath);
    } catch (apiError) {
      setError(apiError instanceof ApiError ? apiError.message : "Unable to sign in");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <GuestOnly>
      <AuthShell
        title="Sign in"
        altHref={`/register${nextPath !== "/" ? `?next=${encodeURIComponent(nextPath)}` : ""}`}
        altLabel="New here?"
      >
        <button
          type="button"
          onClick={() => startGoogleSignIn(nextPath)}
          className="flex h-12 w-full items-center justify-center rounded-2xl border border-slate-300 bg-white text-sm font-semibold text-slate-900 transition hover:bg-slate-50"
        >
          Google
        </button>
        <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-[0.22em] text-slate-400">
          <div className="h-px flex-1 bg-slate-200" />
          <span>or</span>
          <div className="h-px flex-1 bg-slate-200" />
        </div>
        <form onSubmit={submit} className="grid gap-4">
          <label className="grid gap-1.5 text-sm font-medium text-slate-700">
            Email
            <input
              type="email"
              value={form.email}
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              className="h-12 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
              required
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium text-slate-700">
            Password
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              className="h-12 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
              required
            />
          </label>
          {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 h-12 rounded-2xl bg-slate-950 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <div className="mt-5 text-sm text-slate-500">
          New here?{" "}
          <Link href={`/register${nextPath !== "/" ? `?next=${encodeURIComponent(nextPath)}` : ""}`} className="font-semibold text-slate-900 underline decoration-slate-300 underline-offset-4">
            Register
          </Link>
        </div>
      </AuthShell>
    </GuestOnly>
  );
}
