"use client";

import { Check, Loader2 } from "lucide-react";
import type { TimelineStep } from "@/lib/types";

export function RunTimeline({ steps }: { steps: TimelineStep[] }) {
  return (
    <section className="rounded-xl border border-line bg-panel shadow-soft">
      <div className="grid gap-3 p-4 sm:grid-cols-5">
        {steps.map((step) => {
          const Icon = step.icon;
          const active = step.status === "running";
          const done = step.status === "completed";
          const failed = step.status === "failed" || step.status === "error";
          return (
            <div key={step.id} className="min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${
                    done
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : active
                        ? "border-blue-200 bg-blue-50 text-blue-700"
                        : failed
                          ? "border-red-200 bg-red-50 text-red-700"
                          : "border-line bg-slate-50 text-muted"
                  }`}
                >
                  {done ? <Check size={15} /> : active ? <Loader2 size={15} className="animate-spin" /> : Icon ? <Icon size={15} /> : null}
                </span>
                <div className="truncate text-xs font-semibold">{step.label}</div>
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-slate-100">
                <div className={`h-full rounded-full ${done ? "w-full bg-emerald-500" : active ? "w-2/3 bg-blue-500" : failed ? "w-full bg-red-500" : "w-0 bg-slate-300"}`} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
