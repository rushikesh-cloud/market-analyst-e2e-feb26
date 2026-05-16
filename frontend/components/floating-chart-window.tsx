"use client";

import { useState } from "react";
import { BarChart3, Loader2, Maximize2, X } from "lucide-react";
import type { AgentOutput } from "@/lib/types";

function MockTechnicalChart({ visible }: { visible: boolean }) {
  return (
    <div className="h-48 rounded-lg border border-line bg-slate-50 p-3">
      {visible ? (
        <svg viewBox="0 0 420 160" className="h-full w-full" role="img" aria-label="Mock technical chart">
          <path d="M0 128 C50 112 72 120 110 92 C152 60 174 76 210 62 C252 46 282 58 318 34 C356 10 382 24 420 18" fill="none" stroke="#2563eb" strokeWidth="4" />
          <path d="M0 118 C52 108 92 104 132 90 C188 70 236 65 284 52 C340 35 378 30 420 28" fill="none" stroke="#94a3b8" strokeWidth="2" strokeDasharray="5 6" />
          <line x1="0" y1="126" x2="420" y2="126" stroke="#e2e8f0" />
          <line x1="0" y1="82" x2="420" y2="82" stroke="#e2e8f0" />
          <line x1="0" y1="38" x2="420" y2="38" stroke="#e2e8f0" />
        </svg>
      ) : (
        <div className="flex h-full items-center justify-center gap-2 text-xs font-medium text-muted">
          <Loader2 size={14} className="animate-spin" />
          Chart pending
        </div>
      )}
    </div>
  );
}

export function FloatingChartWindow({ output, chartReady }: { output: AgentOutput; chartReady: boolean }) {
  const [open, setOpen] = useState(false);
  const hasRating = typeof output.rating === "number";

  return (
    <div className="fixed bottom-5 right-5 z-30 flex max-w-[calc(100vw-2.5rem)] flex-col items-end gap-3">
      {open ? (
        <section className="w-[360px] max-w-full rounded-xl border border-line bg-panel shadow-soft">
          <div className="flex items-center justify-between gap-3 border-b border-line p-3">
            <div className="flex min-w-0 items-center gap-2">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <BarChart3 size={16} />
              </span>
              <div className="min-w-0">
                <h2 className="truncate text-sm font-semibold">Technical Chart</h2>
                <p className="truncate text-[11px] text-muted">{hasRating ? `${output.rating}/100 rating` : "Waiting for analysis"}</p>
              </div>
            </div>
            <button type="button" onClick={() => setOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-slate-50" aria-label="Close chart">
              <X size={15} />
            </button>
          </div>
          <div className="grid gap-3 p-3">
            <MockTechnicalChart visible={chartReady} />
            <div className="max-h-28 overflow-y-auto rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-700 thin-scrollbar">
              {output.stream || "The technical agent answer will appear here once chart analysis starts."}
            </div>
          </div>
        </section>
      ) : null}
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex h-12 items-center gap-2 rounded-full bg-ink px-4 text-sm font-semibold text-white shadow-soft"
        aria-label="Open technical chart"
      >
        <BarChart3 size={18} />
        <span>Chart</span>
        <Maximize2 size={14} />
      </button>
    </div>
  );
}
