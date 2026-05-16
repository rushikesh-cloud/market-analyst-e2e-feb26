"use client";

import Link from "next/link";
import { CheckCircle2, Circle, Loader2, Search } from "lucide-react";
import type { AgentKey, AgentStatus, WorkflowRun } from "@/lib/types";

const agentLabels: Record<AgentKey, string> = {
  fundamental: "F",
  technical: "T",
  news: "N",
};

function statusClass(status: AgentStatus) {
  if (status === "completed") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "running") return "border-blue-200 bg-blue-50 text-blue-700";
  if (status === "error") return "border-red-200 bg-red-50 text-red-700";
  return "border-line bg-slate-50 text-muted";
}

function StatusIcon({ status }: { status: WorkflowRun["status"] }) {
  if (status === "completed") return <CheckCircle2 size={16} className="text-emerald-600" />;
  if (status === "running") return <Loader2 size={16} className="animate-spin text-blue-600" />;
  return <Circle size={16} className="text-muted" />;
}

export function WorkflowList({
  workflows,
  query,
  onQueryChange,
}: {
  workflows: WorkflowRun[];
  query: string;
  onQueryChange: (query: string) => void;
}) {
  const visible = workflows.filter((workflow) => {
    const haystack = `${workflow.companyName} ${workflow.ticker} ${workflow.sector ?? ""}`.toLowerCase();
    return haystack.includes(query.toLowerCase());
  });

  return (
    <section className="min-w-0 rounded-xl border border-line bg-panel shadow-soft">
      <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-base font-semibold">Workflows</h1>
          <p className="mt-0.5 text-xs text-muted">Stock research runs and supervisor outcomes.</p>
        </div>
        <label className="flex h-9 min-w-0 items-center gap-2 rounded-lg border border-line bg-white px-3 text-xs text-muted sm:w-72">
          <Search size={15} />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search stock"
            className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-muted"
          />
        </label>
      </div>
      <div className="divide-y divide-line">
        {visible.map((workflow) => (
          <Link key={workflow.id} href={`/runs/${workflow.id}`} className="grid gap-4 p-4 transition hover:bg-slate-50 sm:grid-cols-[1fr_auto_auto] sm:items-center">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <StatusIcon status={workflow.status} />
                <div className="truncate text-sm font-semibold">{workflow.companyName}</div>
                <div className="rounded-md border border-line px-1.5 py-0.5 text-[11px] font-medium text-muted">{workflow.ticker}</div>
              </div>
              <div className="mt-1 truncate text-xs text-muted">{workflow.sector ?? "Sector pending"} · {workflow.updatedAt}</div>
            </div>
            <div className="flex items-center gap-1.5">
              {(Object.keys(agentLabels) as AgentKey[]).map((agent) => (
                <span
                  key={agent}
                  className={`flex h-7 w-7 items-center justify-center rounded-full border text-[11px] font-semibold ${statusClass(workflow.agentStatus[agent])}`}
                  title={agent}
                >
                  {agentLabels[agent]}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-2 sm:justify-end">
              <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted">{workflow.status}</span>
              <span className="flex h-9 w-12 items-center justify-center rounded-lg border border-line bg-white text-sm font-semibold">
                {workflow.finalRating ?? "--"}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
