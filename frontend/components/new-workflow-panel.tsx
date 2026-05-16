"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, Play } from "lucide-react";
import type { NewWorkflowDraft } from "@/lib/types";

export function NewWorkflowPanel() {
  const router = useRouter();
  const [draft, setDraft] = useState<NewWorkflowDraft>({
    companyName: "Tata Consultancy Services",
    ticker: "TCS.NS",
    sector: "IT Services",
  });

  function update(field: keyof NewWorkflowDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = `run-${draft.ticker.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`;
    window.sessionStorage.setItem("market-analyst:new-run", JSON.stringify({ id, ...draft }));
    router.push(`/runs/${id}`);
  }

  return (
    <section className="rounded-xl border border-line bg-panel shadow-soft">
      <div className="border-b border-line p-4">
        <h2 className="text-sm font-semibold">New Workflow</h2>
        <p className="mt-0.5 text-xs text-muted">Start the supervisor and all three agents.</p>
      </div>
      <form onSubmit={submit} className="grid gap-3 p-4">
        <label className="grid gap-1.5 text-xs font-medium text-muted">
          Company
          <input
            value={draft.companyName}
            onChange={(event) => update("companyName", event.target.value)}
            className="h-10 rounded-lg border border-line px-3 text-sm text-ink outline-none"
            required
          />
        </label>
        <label className="grid gap-1.5 text-xs font-medium text-muted">
          Ticker
          <input
            value={draft.ticker}
            onChange={(event) => update("ticker", event.target.value.toUpperCase())}
            className="h-10 rounded-lg border border-line px-3 text-sm text-ink outline-none"
            required
          />
        </label>
        <label className="grid gap-1.5 text-xs font-medium text-muted">
          Sector
          <input
            value={draft.sector ?? ""}
            onChange={(event) => update("sector", event.target.value)}
            className="h-10 rounded-lg border border-line px-3 text-sm text-ink outline-none"
          />
        </label>
        <button
          type="button"
          className="flex h-10 items-center justify-center gap-2 rounded-lg border border-dashed border-line text-xs font-medium text-muted"
        >
          <FileUp size={15} />
          Report placeholder
        </button>
        <button type="submit" className="mt-1 flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white">
          <Play size={15} fill="currentColor" />
          Start
        </button>
      </form>
    </section>
  );
}
