"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, RotateCw, Share2 } from "lucide-react";
import { AgentPanel } from "@/components/agent-panel";
import { ChatPanel } from "@/components/chat-panel";
import { FloatingChartWindow } from "@/components/floating-chart-window";
import { RunTimeline } from "@/components/run-timeline";
import { SupervisorPanel } from "@/components/supervisor-panel";
import { getSupervisorRun } from "@/lib/api";
import { baseAgentOutputs, mockChatMessages, timelineSteps } from "@/lib/mock-data";
import type { AgentKey, AgentOutput, SupervisorOutput, SupervisorResult, SupervisorRun, WorkerResult } from "@/lib/types";


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

export function RunWorkspace({ runId }: { runId: string }) {
  const [run, setRun] = useState<SupervisorRun | null>(null);
  const [agents, setAgents] = useState<Record<AgentKey, AgentOutput>>(() => cloneAgentOutputs());
  const [supervisor, setSupervisor] = useState<SupervisorOutput>(initialSupervisor);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const loadRun = () =>
      getSupervisorRun(runId)
        .then((item) => {
          if (!isMounted) return;
          setRun(item);
          setAgents(buildAgentOutputs(item));
          setSupervisor(buildSupervisorOutput(item));
          setError(null);
        })
        .catch((apiError: unknown) => {
          if (isMounted) setError(apiError instanceof Error ? apiError.message : "Unable to load supervisor run");
        });

    loadRun();
    const intervalId = window.setInterval(loadRun, 4000);
    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [runId]);

  useEffect(() => {
    if (!run) return;
    const startedAt = new Date(run.createdAt).getTime();
    if (Number.isNaN(startedAt)) return;
    const intervalId = window.setInterval(() => {
      setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    }, 1000);
    setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    return () => window.clearInterval(intervalId);
  }, [run]);

  const steps = useMemo(
    () =>
      timelineSteps.map((step) => {
        if (step.id === "fundamental") {
          return { ...step, status: run?.fundamentalStatus ?? "idle" };
        }
        if (step.id === "technical") {
          return { ...step, status: run?.technicalStatus ?? "idle" };
        }
        if (step.id === "news") {
          return { ...step, status: run?.newsStatus ?? "idle" };
        }
        if (step.id === "supervisor") {
          return { ...step, status: normalizeAgentStatus(run?.status) };
        }
        return step;
      }),
    [run],
  );

  if (error) {
    return <div className="p-4 text-sm text-red-700 md:p-6">{error}</div>;
  }

  if (!run) {
    return <div className="p-4 text-sm text-muted md:p-6">Loading supervisor run...</div>;
  }

  const chartReady = Boolean(run.technical?.chart_path);

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
              <span className="rounded-md border border-line bg-panel px-2 py-1 text-[11px] font-semibold text-muted">{run.yahooFinanceTicker ?? run.ticker}</span>
            </div>
            <div className="mt-1 text-xs text-muted">{run.sector ?? "Sector pending"} · {run.status} · {elapsed}s</div>
            <div className="mt-1 truncate text-[11px] text-muted">{run.documentName}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex h-9 items-center gap-2 rounded-lg border border-line bg-panel px-3 text-xs font-semibold" disabled>
            <RotateCw size={14} />
            Rerun
          </button>
          <button className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-panel" aria-label="Share">
            <Share2 size={14} />
          </button>
          <div className="flex h-9 w-14 items-center justify-center rounded-lg bg-ink text-sm font-semibold text-white">{run.finalRating ?? "--"}</div>
        </div>
      </div>

      {run.errorMessage ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{run.errorMessage}</div> : null}

      <RunTimeline steps={steps} />

      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <div className="grid gap-5">
          <div className="grid gap-3">
            <AgentPanel output={agents.fundamental} defaultOpen />
            <AgentPanel output={agents.technical} />
            <AgentPanel output={agents.news} />
          </div>
          <SupervisorPanel output={supervisor} />
        </div>
        <ChatPanel enabled={run.status === "completed"} initialMessages={mockChatMessages} />
      </div>
      <FloatingChartWindow output={agents.technical} chartReady={chartReady} />
    </div>
  );
}

function buildAgentOutputs(run: SupervisorRun): Record<AgentKey, AgentOutput> {
  const outputs = cloneAgentOutputs();
  outputs.fundamental = hydrateAgentOutput(outputs.fundamental, run.fundamental, run.fundamentalStatus);
  outputs.technical = hydrateAgentOutput(outputs.technical, run.technical, run.technicalStatus);
  outputs.news = hydrateAgentOutput(outputs.news, run.news, run.newsStatus);
  return outputs;
}

function hydrateAgentOutput(base: AgentOutput, worker: WorkerResult | null | undefined, status: string): AgentOutput {
  const normalizedStatus = normalizeAgentStatus(status);
  if (!worker) {
    return {
      key: base.key,
      title: base.title,
      status: normalizedStatus,
      stream: status === "running" ? "Worker is executing on the backend." : "",
      evidence: [],
      details: {},
    };
  }

  const displayWorker = buildDisplayWorker(worker);

  return {
    key: base.key,
    title: base.title,
    rating: extractWorkerRating(worker, displayWorker),
    stream: buildWorkerSummary(worker, displayWorker, normalizedStatus),
    evidence: extractEvidence(displayWorker),
    details: extractDetails(displayWorker),
    status: normalizedStatus,
  };
}

function buildSupervisorOutput(run: SupervisorRun): SupervisorOutput {
  const supervisor = (run.supervisor ?? {}) as SupervisorResult;
  const weights = supervisor.metadata?.weights ?? {};
  return {
    rating: typeof supervisor.final_rating === "number" ? supervisor.final_rating : run.finalRating,
    status: normalizeAgentStatus(run.status),
    summary: typeof supervisor.summary === "string" ? supervisor.summary : run.status === "running" ? "Supervisor workflow is still executing." : "",
    weights: {
      fundamental: weights.fundamental ?? 0.45,
      technical: weights.technical ?? 0.3,
      news: weights.news ?? 0.25,
    },
  };
}

function extractEvidence(worker: WorkerResult): string[] {
  const entries = Object.entries(worker)
    .filter(([key, value]) => Array.isArray(value) && value.length > 0 && !["sources"].includes(key))
    .flatMap(([, value]) => (value as unknown[]).map((item) => String(item)));
  return entries.slice(0, 6);
}

function extractDetails(worker: WorkerResult): Record<string, string | string[]> {
  const details: Record<string, string | string[]> = {};
  Object.entries(worker).forEach(([key, value]) => {
    if (["answer", "rating", "question", "chart_path", "artifact"].includes(key) || value == null) return;
    if (Array.isArray(value)) {
      details[prettyLabel(key)] = value.map((item) => String(item));
      return;
    }
    if (typeof value === "object") {
      const formatted = formatNestedValue(value);
      if (formatted) {
        details[prettyLabel(key)] = formatted;
      }
      return;
    }
    details[prettyLabel(key)] = String(value);
  });
  if (Object.keys(details).length === 0 && typeof worker.question === "string") {
    details.Question = worker.question;
  }
  return details;
}

function prettyLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function buildDisplayWorker(worker: WorkerResult): WorkerResult {
  const parsedAnswer = parseJsonObject(worker.answer);
  if (!parsedAnswer) {
    return worker;
  }

  return {
    ...parsedAnswer,
    company_name: worker.company_name ?? readString(parsedAnswer.company_name),
    ticker: worker.ticker ?? readString(parsedAnswer.ticker),
    sector: worker.sector ?? readString(parsedAnswer.sector),
    question: worker.question,
    answer: worker.answer,
    rating: worker.rating,
    chart_path: worker.chart_path,
    artifact: worker.artifact,
  };
}

function buildWorkerSummary(worker: WorkerResult, displayWorker: WorkerResult, status: AgentOutput["status"]): string {
  const parsedAnswer = parseJsonObject(worker.answer);
  if (parsedAnswer) {
    const structuredSummary = firstStructuredSummary(parsedAnswer);
    if (structuredSummary) {
      return structuredSummary;
    }
  }

  if (typeof worker.answer === "string" && worker.answer.trim()) {
    return worker.answer;
  }

  if (status === "running") {
    return "Worker is executing on the backend.";
  }

  const fallbackSummary = firstStructuredSummary(displayWorker);
  return fallbackSummary ?? "";
}

function extractWorkerRating(worker: WorkerResult, displayWorker: WorkerResult): number | undefined {
  if (typeof worker.rating === "number") {
    return worker.rating;
  }

  const candidates = ["fundamental_rating", "technical_rating", "news_rating", "sentiment_score", "score"];
  for (const key of candidates) {
    const value = displayWorker[key];
    if (typeof value === "number") {
      return value;
    }
  }

  return undefined;
}

function parseJsonObject(value: unknown): WorkerResult | null {
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed.startsWith("{")) {
    return null;
  }

  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as WorkerResult) : null;
  } catch {
    return null;
  }
}

function firstStructuredSummary(payload: WorkerResult): string | null {
  const preferredFields = ["rationale", "trend", "summary", "sector_context", "stock_implications", "support_resistance"];
  for (const field of preferredFields) {
    const value = payload[field];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }

  const preferredLists = ["positive_developments", "negative_developments", "watch_items", "growth", "risks"];
  for (const field of preferredLists) {
    const value = payload[field];
    if (Array.isArray(value) && value.length > 0) {
      return String(value[0]);
    }
  }

  return null;
}

function formatNestedValue(value: unknown): string | string[] | null {
  if (Array.isArray(value)) {
    return value.map((item) => String(item));
  }

  if (!value || typeof value !== "object") {
    return value == null ? null : String(value);
  }

  const record = value as Record<string, unknown>;
  if (typeof record.title === "string" && typeof record.url === "string") {
    return `${record.title} (${record.url})`;
  }

  const parts = Object.entries(record)
    .map(([key, item]) => {
      if (item == null) return null;
      return `${prettyLabel(key)}: ${Array.isArray(item) ? item.join(", ") : String(item)}`;
    })
    .filter((item): item is string => Boolean(item));

  if (parts.length === 0) {
    return null;
  }

  return parts;
}

function readString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function normalizeAgentStatus(status: string | undefined): AgentOutput["status"] {
  if (status === "queued") return "idle";
  if (status === "failed") return "error";
  if (status === "running" || status === "completed" || status === "error" || status === "idle") return status;
  return "idle";
}
