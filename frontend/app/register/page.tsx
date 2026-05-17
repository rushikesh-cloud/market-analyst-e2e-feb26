"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GuestOnly, useAuth } from "@/components/auth-provider";
import { AuthShell } from "@/components/auth-shell";
import { ApiError } from "@/lib/api";

const inputClassName =
  "h-12 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white";

export default function RegisterPage() {
  const { register, startGoogleSignIn } = useAuth();
  const router = useRouter();
  const [nextPath, setNextPath] = useState("/");
  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    email: "",
    mobileNumber: "",
    gender: "",
    dob: "",
    password: "",
    confirmPassword: "",
  });
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
      await register(form);
      router.replace(nextPath);
    } catch (apiError) {
      setError(apiError instanceof ApiError ? apiError.message : "Unable to create account");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <GuestOnly>
      <AuthShell
        title="Register"
      >
        <button
          type="button"
          onClick={() => startGoogleSignIn(nextPath)}
          className="flex h-12 w-full items-center justify-center rounded-2xl border border-slate-300 bg-white text-sm font-semibold text-slate-900 transition hover:bg-slate-50"
        >
          Google
        </button>
        <div className="my-6 flex items-center gap-3 text-[11px] uppercase tracking-[0.22em] text-slate-400">
          <div className="h-px flex-1 bg-slate-200" />
          <span>or</span>
          <div className="h-px flex-1 bg-slate-200" />
        </div>
        <form onSubmit={submit} className="grid gap-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="First name">
              <input value={form.firstName} onChange={(event) => setForm((current) => ({ ...current, firstName: event.target.value }))} className={inputClassName} required />
            </Field>
            <Field label="Last name">
              <input value={form.lastName} onChange={(event) => setForm((current) => ({ ...current, lastName: event.target.value }))} className={inputClassName} required />
            </Field>
          </div>
          <Field label="Email">
            <input type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} className={inputClassName} required />
          </Field>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Mobile number">
              <input value={form.mobileNumber} onChange={(event) => setForm((current) => ({ ...current, mobileNumber: event.target.value }))} className={inputClassName} required />
            </Field>
            <Field label="Gender">
              <select value={form.gender} onChange={(event) => setForm((current) => ({ ...current, gender: event.target.value }))} className={inputClassName} required>
                <option value="">Select</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="non_binary">Non-binary</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </Field>
          </div>
          <Field label="Date of birth">
            <input type="date" value={form.dob} onChange={(event) => setForm((current) => ({ ...current, dob: event.target.value }))} className={inputClassName} required />
          </Field>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Password">
              <input type="password" value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} className={inputClassName} required />
            </Field>
            <Field label="Confirm password">
              <input type="password" value={form.confirmPassword} onChange={(event) => setForm((current) => ({ ...current, confirmPassword: event.target.value }))} className={inputClassName} required />
            </Field>
          </div>
          {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-3 h-12 rounded-2xl bg-slate-950 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Creating account..." : "Create account"}
          </button>
        </form>
        <div className="mt-6 text-sm text-slate-500">
          Already registered?{" "}
          <Link href={`/login${nextPath !== "/" ? `?next=${encodeURIComponent(nextPath)}` : ""}`} className="font-semibold text-slate-900 underline decoration-slate-300 underline-offset-4">
            Login
          </Link>
        </div>
      </AuthShell>
    </GuestOnly>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-2 text-sm font-medium text-slate-700">
      <span>{label}</span>
      {children}
    </label>
  );
}
