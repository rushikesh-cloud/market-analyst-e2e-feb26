"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { NewWorkflowPanel } from "@/components/new-workflow-panel";
import { WorkflowList } from "@/components/workflow-list";
import { listSupervisorRuns } from "@/lib/api";
import type { SupervisorRun } from "@/lib/types";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [runs, setRuns] = useState<SupervisorRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadRuns = () =>
      listSupervisorRuns()
        .then((items) => {
          if (isMounted) setRuns(items);
        })
        .catch((apiError: unknown) => {
          if (isMounted) setError(apiError instanceof Error ? apiError.message : "Unable to load workflows");
        });

    loadRuns();
    const intervalId = window.setInterval(loadRuns, 5000);
    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, []);

  return (
    <AppShell>
      <div className="grid gap-5 p-4 md:p-6 xl:grid-cols-[1fr_340px]">
        <div className="grid gap-5">
          {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
          <WorkflowList workflows={runs} query={query} onQueryChange={setQuery} />
        </div>
        <div className="grid content-start gap-5">
          <NewWorkflowPanel />
          <section className="rounded-xl border border-line bg-panel p-4 shadow-soft">
            <h2 className="text-sm font-semibold">Workflow Rules</h2>
            <div className="mt-3 grid gap-2 text-xs text-muted">
              <div className="rounded-lg bg-slate-50 px-3 py-2">Select an existing company first.</div>
              <div className="rounded-lg bg-slate-50 px-3 py-2">Choose a completed document from the library.</div>
              <div className="rounded-lg bg-slate-50 px-3 py-2">The backend starts the supervisor workflow and persists the run state.</div>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
