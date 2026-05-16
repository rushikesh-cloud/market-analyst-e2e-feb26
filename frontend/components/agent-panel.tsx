"use client";

import { BarChart3, CheckCircle2, FileSearch, Loader2, Newspaper } from "lucide-react";
import type { AgentKey, AgentOutput } from "@/lib/types";

const icons = {
  fundamental: FileSearch,
  technical: BarChart3,
  news: Newspaper,
} satisfies Record<AgentKey, typeof FileSearch>;

function Rating({ value }: { value?: number }) {
  return (
    <div className="flex h-10 w-12 items-center justify-center rounded-lg border border-line bg-white text-sm font-semibold">
      {value ?? "--"}
    </div>
  );
}

function MiniChart({ visible }: { visible: boolean }) {
  return (
    <div className="h-44 rounded-lg border border-line bg-slate-50 p-3">
      {visible ? (
        <svg viewBox="0 0 420 160" className="h-full w-full" role="img" aria-label="Mock technical chart">
          <path d="M0 128 C50 112 72 120 110 92 C152 60 174 76 210 62 C252 46 282 58 318 34 C356 10 382 24 420 18" fill="none" stroke="#2563eb" strokeWidth="4" />
          <path d="M0 118 C52 108 92 104 132 90 C188 70 236 65 284 52 C340 35 378 30 420 28" fill="none" stroke="#94a3b8" strokeWidth="2" strokeDasharray="5 6" />
          <line x1="0" y1="126" x2="420" y2="126" stroke="#e2e8f0" />
          <line x1="0" y1="82" x2="420" y2="82" stroke="#e2e8f0" />
          <line x1="0" y1="38" x2="420" y2="38" stroke="#e2e8f0" />
        </svg>
      ) : (
        <div className="flex h-full items-center justify-center text-xs font-medium text-muted">Chart pending</div>
      )}
    </div>
  );
}

export function AgentPanel({ output, chartReady }: { output: AgentOutput; chartReady?: boolean }) {
  const Icon = icons[output.key];
  const isRunning = output.status === "running";
  const isCompleted = output.status === "completed";

  return (
    <section className="min-w-0 rounded-xl border border-line bg-panel shadow-soft">
      <div className="flex items-center justify-between gap-3 border-b border-line p-4">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-ink">
            <Icon size={16} />
          </span>
          <h2 className="truncate text-sm font-semibold">{output.title}</h2>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? <Loader2 size={15} className="animate-spin text-blue-600" /> : isCompleted ? <CheckCircle2 size={15} className="text-emerald-600" /> : null}
          <Rating value={output.rating} />
        </div>
      </div>
      <div className="grid gap-4 p-4">
        {output.key === "technical" ? <MiniChart visible={Boolean(chartReady)} /> : null}
        <div className="min-h-24 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          {output.stream ? <span className={isRunning ? "stream-cursor" : ""}>{output.stream}</span> : <span className="text-muted">Waiting for agent stream.</span>}
        </div>
        <div className="grid gap-2">
          <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Evidence</div>
          {output.evidence.map((item) => (
            <div key={item} className="rounded-lg border border-line px-3 py-2 text-xs leading-5 text-slate-700">
              {item}
            </div>
          ))}
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          {Object.entries(output.details).map(([label, value]) => (
            <div key={label} className="min-w-0 rounded-lg bg-slate-50 p-3">
              <div className="text-[11px] font-semibold text-muted">{label}</div>
              <div className="mt-1 text-xs leading-5 text-slate-700">{Array.isArray(value) ? value.join(", ") : value}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
