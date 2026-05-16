"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, RotateCw, Share2 } from "lucide-react";
import { AgentPanel } from "@/components/agent-panel";
import { ChatPanel } from "@/components/chat-panel";
import { RunTimeline } from "@/components/run-timeline";
import { SupervisorPanel } from "@/components/supervisor-panel";
import { baseAgentOutputs, mockChatMessages, mockWorkflows, timelineSteps } from "@/lib/mock-data";
import { subscribeToMockRun } from "@/lib/mock-stream";
import type { AgentKey, AgentOutput, AgentStatus, RunEvent, SupervisorOutput, WorkflowRun } from "@/lib/types";

function cloneAgentOutputs(): Record<AgentKey, AgentOutput> {
  return {
    fundamental: { ...baseAgentOutputs.fundamental, details: { ...baseAgentOutputs.fundamental.details }, evidence: [...baseAgentOutputs.fundamental.evidence] },
    technical: { ...baseAgentOutputs.technical, details: { ...baseAgentOutputs.technical.details }, evidence: [...baseAgentOutputs.technical.evidence] },
    news: { ...baseAgentOutputs.news, details: { ...baseAgentOutputs.news.details }, evidence: [...baseAgentOutputs.news.evidence] },
  };
}

const initialSupervisor: SupervisorOutput = {
  status: "idle",
  summary: "",
  weights: { fundamental: 0.45, technical: 0.3, news: 0.25 },
};

function fallbackRun(id: string): WorkflowRun {
  return {
    id,
    companyName: "Tata Consultancy Services",
    ticker: "TCS.NS",
    sector: "IT Services",
    status: "running",
    updatedAt: "Now",
    agentStatus: { fundamental: "idle", technical: "idle", news: "idle" },
  };
}

function nextAgentState(current: Record<AgentKey, AgentOutput>, agent: AgentKey, status: AgentStatus, patch: Partial<AgentOutput> = {}) {
  return {
    ...current,
    [agent]: {
      ...current[agent],
      ...patch,
      status,
    },
  };
}

export function RunWorkspace({ runId }: { runId: string }) {
  const [run, setRun] = useState<WorkflowRun>(() => mockWorkflows.find((item) => item.id === runId) ?? fallbackRun(runId));
  const [agents, setAgents] = useState<Record<AgentKey, AgentOutput>>(() => cloneAgentOutputs());
  const [supervisor, setSupervisor] = useState<SupervisorOutput>(initialSupervisor);
  const [chartReady, setChartReady] = useState(false);
  const [startedAt] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const saved = window.sessionStorage.getItem("market-analyst:new-run");
    if (!saved) return;
    try {
      const draft = JSON.parse(saved) as Partial<WorkflowRun>;
      if (draft.id === runId) {
        setRun((current) => ({
          ...current,
          companyName: String(draft.companyName ?? current.companyName),
          ticker: String(draft.ticker ?? current.ticker),
          sector: String(draft.sector ?? current.sector ?? ""),
        }));
      }
    } catch {
      window.sessionStorage.removeItem("market-analyst:new-run");
    }
  }, [runId]);

  useEffect(() => {
    const interval = window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => window.clearInterval(interval);
  }, [startedAt]);

  useEffect(() => {
    setAgents(cloneAgentOutputs());
    setSupervisor(initialSupervisor);
    setChartReady(false);
    return subscribeToMockRun((event) => applyEvent(event));
  }, [runId]);

  function applyEvent(event: RunEvent) {
    if (event.type === "run_started") {
      setRun((current) => ({ ...current, status: "running" }));
      return;
    }
    if (event.type === "agent_started") {
      setAgents((current) => nextAgentState(current, event.agent, "running"));
      setRun((current) => ({ ...current, agentStatus: { ...current.agentStatus, [event.agent]: "running" } }));
      return;
    }
    if (event.type === "agent_chunk") {
      setAgents((current) =>
        nextAgentState(current, event.agent, "running", {
          stream: `${current[event.agent].stream}${event.content}`,
        }),
      );
      return;
    }
    if (event.type === "chart_ready") {
      setChartReady(true);
      return;
    }
    if (event.type === "agent_completed") {
      setAgents((current) => nextAgentState(current, event.agent, "completed", { rating: event.rating }));
      setRun((current) => ({ ...current, agentStatus: { ...current.agentStatus, [event.agent]: "completed" } }));
      return;
    }
    if (event.type === "supervisor_started") {
      setSupervisor((current) => ({ ...current, status: "running" }));
      return;
    }
    if (event.type === "supervisor_chunk") {
      setSupervisor((current) => ({ ...current, status: "running", summary: `${current.summary}${event.content}` }));
      return;
    }
    if (event.type === "supervisor_completed") {
      setSupervisor((current) => ({ ...current, status: "completed", rating: event.rating }));
      setRun((current) => ({ ...current, status: "completed", finalRating: event.rating, updatedAt: "Just now" }));
    }
  }

  const steps = useMemo(
    () =>
      timelineSteps.map((step) => {
        if (step.id === "fundamental" || step.id === "technical" || step.id === "news") {
          return { ...step, status: agents[step.id].status };
        }
        if (step.id === "supervisor") {
          return { ...step, status: supervisor.status };
        }
        return step;
      }),
    [agents, supervisor.status],
  );

  return (
    <div className="grid gap-5 p-4 md:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <Link href="/" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line bg-panel" aria-label="Back">
            <ArrowLeft size={16} />
          </Link>
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-2">
              <h1 className="truncate text-lg font-semibold">{run.companyName}</h1>
              <span className="rounded-md border border-line bg-panel px-2 py-1 text-[11px] font-semibold text-muted">{run.ticker}</span>
            </div>
            <div className="mt-1 text-xs text-muted">{run.sector ?? "Sector pending"} · {run.status} · {elapsed}s</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex h-9 items-center gap-2 rounded-lg border border-line bg-panel px-3 text-xs font-semibold">
            <RotateCw size={14} />
            Rerun
          </button>
          <button className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-panel" aria-label="Share">
            <Share2 size={14} />
          </button>
          <div className="flex h-9 w-14 items-center justify-center rounded-lg bg-ink text-sm font-semibold text-white">{run.finalRating ?? "--"}</div>
        </div>
      </div>

      <RunTimeline steps={steps} />

      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <div className="grid gap-5">
          <div className="grid gap-5 lg:grid-cols-3">
            <AgentPanel output={agents.fundamental} />
            <AgentPanel output={agents.technical} chartReady={chartReady} />
            <AgentPanel output={agents.news} />
          </div>
          <SupervisorPanel output={supervisor} />
        </div>
        <ChatPanel enabled={supervisor.status === "completed"} initialMessages={mockChatMessages} />
      </div>
    </div>
  );
}
