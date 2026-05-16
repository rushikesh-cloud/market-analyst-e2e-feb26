"use client";

import { Sparkles } from "lucide-react";
import type { SupervisorOutput } from "@/lib/types";

export function SupervisorPanel({ output }: { output: SupervisorOutput }) {
  const active = output.status === "running";
  const completed = output.status === "completed";

  return (
    <section className="rounded-xl border border-line bg-panel shadow-soft">
      <div className="flex items-center justify-between gap-3 border-b border-line p-4">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100">
            <Sparkles size={16} />
          </span>
          <h2 className="text-sm font-semibold">Supervisor</h2>
        </div>
        <div className="flex h-10 w-14 items-center justify-center rounded-lg bg-ink text-sm font-semibold text-white">{output.rating ?? "--"}</div>
      </div>
      <div className="grid gap-4 p-4 lg:grid-cols-[1fr_280px]">
        <div className="min-h-28 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          {output.summary ? <span className={active ? "stream-cursor" : ""}>{output.summary}</span> : <span className="text-muted">Supervisor synthesis pending.</span>}
        </div>
        <div className="grid content-start gap-3">
          {Object.entries(output.weights).map(([label, weight]) => (
            <div key={label}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="capitalize text-muted">{label}</span>
                <span className="font-semibold">{Math.round(weight * 100)}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100">
                <div className={`h-full rounded-full ${completed ? "bg-ink" : "bg-slate-300"}`} style={{ width: `${weight * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
