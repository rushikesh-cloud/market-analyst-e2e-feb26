"use client";

import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { NewWorkflowPanel } from "@/components/new-workflow-panel";
import { WorkflowList } from "@/components/workflow-list";
import { mockWorkflows } from "@/lib/mock-data";

export default function HomePage() {
  const [query, setQuery] = useState("");

  return (
    <AppShell>
      <div className="grid gap-5 p-4 md:p-6 xl:grid-cols-[1fr_340px]">
        <WorkflowList workflows={mockWorkflows} query={query} onQueryChange={setQuery} />
        <div className="grid content-start gap-5">
          <NewWorkflowPanel />
          <section id="agents" className="rounded-xl border border-line bg-panel p-4 shadow-soft">
            <h2 className="text-sm font-semibold">Agents</h2>
            <div className="mt-3 grid gap-2 text-xs text-muted">
              <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2"><span>Fundamentals</span><span>RAG</span></div>
              <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2"><span>Technical</span><span>Chart</span></div>
              <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2"><span>News</span><span>Tavily</span></div>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
