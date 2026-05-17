"use client";

import Link from "next/link";

export function AuthShell({
  title,
  altHref,
  altLabel,
  children,
}: {
  title: string;
  altHref?: string;
  altLabel?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="auth-screen min-h-screen px-4 py-10 sm:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-5xl items-center gap-8 lg:grid-cols-[0.95fr_440px]">
        <section className="hidden rounded-[32px] border border-white/60 bg-white/75 p-10 shadow-[0_32px_90px_rgba(27,38,59,0.12)] backdrop-blur lg:block">
          <div className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-600">
            Market Analyst
          </div>
          <h1 className="mt-6 max-w-lg font-serif text-5xl leading-[1.02] text-slate-900">Private workspace.</h1>
        </section>
        <section className="rounded-[32px] border border-white/70 bg-white/88 p-6 shadow-[0_36px_100px_rgba(31,41,55,0.14)] backdrop-blur sm:p-8">
          <h2 className="font-serif text-4xl text-slate-950">{title}</h2>
          <div className="mt-8">{children}</div>
          {altHref && altLabel ? (
            <div className="mt-6 text-sm text-slate-500">
              {altLabel}{" "}
              <Link href={altHref} className="font-semibold text-slate-900 underline decoration-slate-300 underline-offset-4">
                Open it
              </Link>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
