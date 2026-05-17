"use client";

import Image from "next/image";
import { useState } from "react";
import { BarChart3, CheckCircle2, ChevronDown, FileSearch, Loader2, Newspaper } from "lucide-react";
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

export function AgentPanel({ output, defaultOpen = false }: { output: AgentOutput; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const Icon = icons[output.key];
  const isRunning = output.status === "running";
  const isCompleted = output.status === "completed";
  const preview = output.stream || "Waiting for agent stream.";
  const hasEvidence = output.evidence.length > 0;
  const hasDetails = Object.keys(output.details).length > 0;
  const hasSources = output.sources.length > 0;

  return (
    <section className="min-w-0 rounded-xl border border-line bg-panel shadow-soft">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 border-b border-line p-4 text-left"
        aria-expanded={open}
      >
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-ink">
            <Icon size={17} />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold">{output.title}</h2>
            <p className="mt-1 truncate text-xs text-muted">{preview}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? <Loader2 size={15} className="animate-spin text-blue-600" /> : isCompleted ? <CheckCircle2 size={15} className="text-emerald-600" /> : null}
          <Rating value={output.rating} />
          <ChevronDown size={16} className={`text-muted transition ${open ? "rotate-180" : ""}`} />
        </div>
      </button>
      {open ? (
        <div className="grid gap-4 p-4">
          {output.chartUrl ? (
            <div className="overflow-hidden rounded-lg border border-line bg-slate-50">
              <Image
                src={output.chartUrl}
                alt={`${output.title} chart`}
                width={1600}
                height={900}
                unoptimized
                className="h-auto w-full object-contain"
              />
            </div>
          ) : null}
          <div className="min-h-24 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-700">
            {output.stream ? <span className={isRunning ? "stream-cursor" : ""}>{output.stream}</span> : <span className="text-muted">Waiting for agent stream.</span>}
          </div>
          {hasEvidence ? (
            <div className="grid gap-2">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Evidence</div>
              {output.evidence.map((item) => (
                <div key={item} className="rounded-lg border border-line px-3 py-2 text-xs leading-5 text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          ) : null}
          {hasDetails ? (
            <div className="grid gap-2 md:grid-cols-3">
              {Object.entries(output.details).map(([label, value]) => (
                <div key={label} className="min-w-0 rounded-lg bg-slate-50 p-3">
                  <div className="text-[11px] font-semibold text-muted">{label}</div>
                  <div className="mt-1 text-xs leading-5 text-slate-700">{Array.isArray(value) ? value.join(", ") : value}</div>
                </div>
              ))}
            </div>
          ) : null}
          {hasSources ? (
            <div className="grid gap-2">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Sources</div>
              {output.sources.map((source) => (
                source.href ? (
                  <a
                    key={`${source.label}-${source.href}`}
                    href={source.href}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-lg border border-line px-3 py-2 text-xs leading-5 text-blue-700 hover:bg-slate-50"
                  >
                    {source.label}
                  </a>
                ) : (
                  <div key={source.label} className="rounded-lg border border-line px-3 py-2 text-xs leading-5 text-slate-700">
                    {source.label}
                  </div>
                )
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
