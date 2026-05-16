import { AppShell } from "@/components/app-shell";


const agents = [
  {
    title: "Fundamental Agent",
    subtitle: "RAG over ingested company documents",
    details: [
      "Reads Azure Document Intelligence output persisted through the document ingestion pipeline.",
      "Uses hybrid retrieval against report chunks before scoring growth, debt, cash flow, and risk.",
      "Supervisor runs now persist the selected company and document before execution starts.",
    ],
  },
  {
    title: "Technical Agent",
    subtitle: "Chart generation plus multimodal review",
    details: [
      "Uses the company's Yahoo Finance ticker for price history and chart generation.",
      "Persists the technical worker output into each supervisor run for run-detail playback.",
      "The chart panel in run detail activates once the backend has produced the chart artifact.",
    ],
  },
  {
    title: "News Agent",
    subtitle: "Company plus sector context",
    details: [
      "Runs recent company and sector searches through the backend Tavily integration.",
      "Stores rating and structured news context on the supervisor run row.",
      "Feeds the final supervisor outcome with the same persisted agent contract used by the UI.",
    ],
  },
  {
    title: "Supervisor Agent",
    subtitle: "Run orchestrator",
    details: [
      "A workflow can now be started only from an existing company and a completed document.",
      "The backend validates company-document ownership before starting the run.",
      "Each run is persisted so the workflow list and run detail page read from FastAPI instead of mock session state.",
    ],
  },
];


export default function AgentsPage() {
  return (
    <AppShell>
      <div className="grid gap-5 p-4 md:p-6">
        <section className="rounded-xl border border-line bg-panel p-5 shadow-soft">
          <h1 className="text-base font-semibold">Agents</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted">
            This page replaces the old hash-linked summary block. It documents the backend-connected agent surfaces that power supervisor runs.
          </p>
        </section>
        <div className="grid gap-4 xl:grid-cols-2">
          {agents.map((agent) => (
            <section key={agent.title} className="rounded-xl border border-line bg-panel p-5 shadow-soft">
              <div className="text-sm font-semibold">{agent.title}</div>
              <div className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">{agent.subtitle}</div>
              <div className="mt-4 grid gap-2 text-sm text-slate-700">
                {agent.details.map((detail) => (
                  <div key={detail} className="rounded-lg bg-slate-50 px-3 py-2">
                    {detail}
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
