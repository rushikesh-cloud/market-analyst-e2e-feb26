"use client";

import Link from "next/link";

export function AuthShell({
  title,
  eyebrow,
  subtitle,
  altHref,
  altLabel,
  children,
}: {
  title: string;
  eyebrow: string;
  subtitle: string;
  altHref: string;
  altLabel: string;
  children: React.ReactNode;
}) {
  return (
    <div className="auth-screen min-h-screen px-4 py-10 sm:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1.05fr_460px]">
        <section className="hidden rounded-[32px] border border-white/60 bg-white/75 p-10 shadow-[0_32px_90px_rgba(27,38,59,0.12)] backdrop-blur lg:block">
          <div className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-600">
            Market Analyst
          </div>
          <h1 className="mt-6 max-w-xl font-serif text-5xl leading-[1.02] text-slate-900">
            A private market intelligence workspace with a real sign-in boundary.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-slate-600">
            Use local credentials or Google sign-in, then step into the workflow console, company master, and document library as an authenticated operator.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {[
              ["Protected app", "Workflow, company, and document routes stay behind auth."],
              ["Local sign-in", "Email and password remain first-class for direct access."],
              ["Google entry", "OAuth stays available for both sign-in and account creation."],
            ].map(([heading, body]) => (
              <div key={heading} className="rounded-3xl border border-slate-200 bg-slate-50/80 p-4">
                <div className="text-sm font-semibold text-slate-900">{heading}</div>
                <div className="mt-2 text-sm leading-6 text-slate-600">{body}</div>
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-[32px] border border-white/70 bg-white/88 p-6 shadow-[0_36px_100px_rgba(31,41,55,0.14)] backdrop-blur sm:p-8">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">{eyebrow}</div>
          <h2 className="mt-3 font-serif text-4xl text-slate-950">{title}</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-6 text-sm text-slate-500">
            {altLabel}{" "}
            <Link href={altHref} className="font-semibold text-slate-900 underline decoration-slate-300 underline-offset-4">
              Open it
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
