"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, BarChart3, FileSearch, Newspaper, RotateCw, Share2, Sparkles } from "lucide-react";
import { ChatPanel } from "@/components/chat-panel";
import { RunTimeline } from "@/components/run-timeline";
import { getSupervisorRun, getSupervisorRunTechnicalChartUrl } from "@/lib/api";
import { timelineSteps } from "@/lib/mock-data";
import type {
  AgentKey,
  AgentStatus,
  FundamentalVisualSummary,
  NewsVisualSummary,
  SourceReference,
  SupervisorResult,
  SupervisorRun,
  SupervisorVisualSummary,
  TechnicalVisualSummary,
  TimelineStep,
  WorkerResult,
} from "@/lib/types";

type RunTab = "overview" | "fundamental" | "technical" | "news";

const tabConfig: Array<{ id: RunTab; label: string; icon: typeof Sparkles }> = [
  { id: "overview", label: "Overview", icon: Sparkles },
  { id: "fundamental", label: "Fundamental", icon: FileSearch },
  { id: "technical", label: "Technical", icon: BarChart3 },
  { id: "news", label: "News", icon: Newspaper },
];

export function RunWorkspace({ runId }: { runId: string }) {
  const [run, setRun] = useState<SupervisorRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [activeTab, setActiveTab] = useState<RunTab>("overview");

  useEffect(() => {
    let isMounted = true;

    const loadRun = () =>
      getSupervisorRun(runId)
        .then((item) => {
          if (!isMounted) return;
          setRun(item);
          setError(null);
        })
        .catch((apiError: unknown) => {
          if (isMounted) setError(apiError instanceof Error ? apiError.message : "Unable to load supervisor run");
        });

    void loadRun();
    const intervalId = window.setInterval(loadRun, 4000);
    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [runId]);

  useEffect(() => {
    if (!run) return;

    const updateElapsed = () => {
      const startedAt = new Date(run.createdAt).getTime();
      const endedAt = new Date(run.updatedAt).getTime();
      if (Number.isNaN(startedAt)) return;
      const referenceTime =
        run.status === "running"
          ? Date.now()
          : Number.isNaN(endedAt)
            ? startedAt
            : endedAt;
      setElapsed(Math.max(0, Math.floor((referenceTime - startedAt) / 1000)));
    };

    updateElapsed();
    if (run.status !== "running") return;

    const intervalId = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(intervalId);
  }, [run]);

  const steps = useMemo(() => buildTimelineSteps(run), [run]);

  if (error) {
    return <div className="p-4 text-sm text-red-700 md:p-6">{error}</div>;
  }

  if (!run) {
    return <div className="p-4 text-sm text-muted md:p-6">Loading supervisor run...</div>;
  }

  const supervisor = (run.supervisor ?? {}) as SupervisorResult;
  const overview = (supervisor.visual_summary ?? {}) as SupervisorVisualSummary;
  const fundamental = (run.fundamental ?? {}) as WorkerResult;
  const technical = (run.technical ?? {}) as WorkerResult;
  const news = (run.news ?? {}) as WorkerResult;
  const fundamentalVisual = (fundamental.visual_summary ?? {}) as FundamentalVisualSummary;
  const technicalVisual = (technical.visual_summary ?? {}) as TechnicalVisualSummary;
  const newsVisual = (news.visual_summary ?? {}) as NewsVisualSummary;
  const technicalChartUrl = typeof technical.chart_path === "string" ? getSupervisorRunTechnicalChartUrl(run.id) : undefined;
  const componentSummaries =
    overview.component_contributions && overview.component_contributions.length > 0
      ? overview.component_contributions
      : buildFallbackContributions(run);

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
        </div>
      </div>

      {run.errorMessage ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{run.errorMessage}</div> : null}

      <section className="overflow-hidden rounded-2xl bg-slate-950 text-white shadow-soft">
        <div className="grid gap-4 p-5 lg:grid-cols-[1.3fr_0.7fr] lg:p-6">
          <div className="grid gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill label={overview.stance ?? describeStatus(run.status)} tone={toneFromRating(run.finalRating)} />
              {overview.confidence ? <StatusPill label={overview.confidence} tone="neutral" /> : null}
              <StatusPill label={run.documentName} tone="neutral" />
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              {componentSummaries.map((item) => (
                <MiniScoreCard key={item.name} label={item.name} rating={item.rating} />
              ))}
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <SummaryBucket title="Positive" items={overview.top_positives} emptyLabel="Pending" />
              <SummaryBucket title="Risk" items={overview.top_risks} emptyLabel="Pending" />
              <SummaryBucket title="Watch" items={overview.watch_items} emptyLabel="Pending" />
            </div>
          </div>
          <div className="grid gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Final</div>
                <div className="mt-2 text-4xl font-semibold leading-none">{run.finalRating ?? "--"}</div>
              </div>
              <div className="rounded-2xl bg-white/10 px-3 py-2 text-xs font-medium text-slate-200">{run.status}</div>
            </div>
            <div className="grid gap-2">
              {componentSummaries.map((item) => (
                <div key={item.name}>
                  <div className="mb-1 flex items-center justify-between text-xs text-slate-300">
                    <span className="capitalize">{item.name}</span>
                    <span>{item.rating ?? "--"}</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div
                      className={`h-full rounded-full ${toneFillClass(toneFromRating(item.rating))}`}
                      style={{ width: `${Math.max(8, item.weight_pct)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <RunTimeline steps={steps} />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="grid gap-5">
          <section className="rounded-2xl border border-line bg-panel shadow-soft">
            <div className="flex flex-wrap gap-2 border-b border-line p-3">
              {tabConfig.map((tab) => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition ${
                      active ? "bg-slate-950 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    <Icon size={14} />
                    {tab.label}
                  </button>
                );
              })}
            </div>
            <div className="p-4 md:p-5">
              {activeTab === "overview" ? (
                <OverviewTab
                  run={run}
                  overview={overview}
                  componentSummaries={componentSummaries}
                  technicalChartUrl={technicalChartUrl}
                />
              ) : null}
              {activeTab === "fundamental" ? (
                <FundamentalTab
                  status={run.fundamentalStatus}
                  summary={fundamentalVisual}
                  sources={extractFundamentalSources(fundamental)}
                />
              ) : null}
              {activeTab === "technical" ? (
                <TechnicalTab status={run.technicalStatus} summary={technicalVisual} chartUrl={technicalChartUrl} />
              ) : null}
              {activeTab === "news" ? (
                <NewsTab status={run.newsStatus} summary={newsVisual} sources={extractNewsSources(news)} />
              ) : null}
            </div>
          </section>
        </div>
        <div className="xl:sticky xl:top-6 xl:self-start">
          <ChatPanel runId={runId} enabled={run.status === "completed"} initialMessages={[]} />
        </div>
      </div>
    </div>
  );
}

function OverviewTab({
  run,
  overview,
  componentSummaries,
  technicalChartUrl,
}: {
  run: SupervisorRun;
  overview: SupervisorVisualSummary;
  componentSummaries: Array<{ name: string; rating?: number | null; weight_pct: number; contribution_pct?: number | null }>;
  technicalChartUrl?: string;
}) {
  return (
    <div className="grid gap-5">
      <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-line bg-slate-50 p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Decision</div>
          <div className="mt-3 text-sm leading-6 text-slate-800">{overview.decision || minimalStatusCopy(run.status)}</div>
        </section>
        <section className="rounded-2xl border border-line bg-white p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Mix</div>
          <div className="mt-3 grid gap-3">
            {componentSummaries.map((item) => (
              <div key={item.name}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="capitalize text-slate-600">{item.name}</span>
                  <span className="font-semibold text-slate-900">{item.rating ?? "--"}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div className={`h-full rounded-full ${toneFillClass(toneFromRating(item.rating))}`} style={{ width: `${Math.max(10, item.weight_pct)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <ListCard title="Positive" items={overview.top_positives} />
        <ListCard title="Risk" items={overview.top_risks} />
        <ListCard title="Watch" items={overview.watch_items} />
      </div>
      {technicalChartUrl ? (
        <section className="overflow-hidden rounded-2xl border border-line bg-white p-3">
          <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Chart</div>
          <Image
            src={technicalChartUrl}
            alt={`${run.companyName} technical chart`}
            width={1600}
            height={900}
            unoptimized
            className="h-auto w-full rounded-xl border border-line object-contain"
          />
        </section>
      ) : null}
    </div>
  );
}

function FundamentalTab({
  status,
  summary,
  sources,
}: {
  status: AgentStatus;
  summary: FundamentalVisualSummary;
  sources: SourceReference[];
}) {
  if (status !== "completed" && !hasFundamentalContent(summary)) {
    return <MinimalPending status={status} />;
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 md:grid-cols-5">
        <MetricCard label="Stance" value={summary.stance} />
        <MetricCard label="Revenue" value={summary.revenue_display} />
        <MetricCard label="Growth" value={formatPercent(summary.revenue_growth_pct)} />
        <MetricCard label="Margin" value={formatPercent(summary.profit_margin_pct)} />
        <MetricCard label="D/E" value={formatNumber(summary.debt_to_equity)} />
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <ListCard title="Positive" items={summary.top_positives} />
        <ListCard title="Risk" items={summary.top_risks} />
        <ListCard title="Watch" items={summary.watch_items} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <MetricPanel title="Cash Flow" value={summary.cash_flow_view} />
        <MetricPanel title="Valuation" value={summary.valuation_view} />
      </div>
      <SourceSection title="Sources" items={sources} />
    </div>
  );
}

function TechnicalTab({
  status,
  summary,
  chartUrl,
}: {
  status: AgentStatus;
  summary: TechnicalVisualSummary;
  chartUrl?: string;
}) {
  if (status !== "completed" && !hasTechnicalContent(summary) && !chartUrl) {
    return <MinimalPending status={status} />;
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 md:grid-cols-6">
        <MetricCard label="Stance" value={summary.stance} />
        <MetricCard label="Price" value={formatNumber(summary.current_price)} />
        <MetricCard label="RSI" value={formatNumber(summary.rsi)} />
        <MetricCard label="vs MA20" value={formatPercent(summary.distance_to_ma20_pct)} />
        <MetricCard label="vs MA50" value={formatPercent(summary.distance_to_ma50_pct)} />
        <MetricCard label="MACD" value={summary.macd_signal_state} />
      </div>
      <div className="grid gap-3 lg:grid-cols-[1.25fr_0.75fr]">
        <section className="overflow-hidden rounded-2xl border border-line bg-white p-3">
          <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Chart</div>
          {chartUrl ? (
            <Image
              src={chartUrl}
              alt="Technical chart"
              width={1600}
              height={900}
              unoptimized
              className="h-auto w-full rounded-xl border border-line object-contain"
            />
          ) : (
            <div className="rounded-xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">Pending</div>
          )}
        </section>
        <div className="grid gap-3">
          <MetricPanel title="Trend" value={summary.trend_state} />
          <MetricPanel title="Momentum" value={summary.momentum_state} />
          <MetricPanel title="Setup" value={summary.setup} />
        </div>
      </div>
      <div className="grid gap-3 lg:grid-cols-4">
        <ListCard title="Support" items={summary.support_levels} />
        <ListCard title="Resistance" items={summary.resistance_levels} />
        <ListCard title="Risk" items={summary.top_risks} />
        <ListCard title="Watch" items={summary.watch_items} />
      </div>
    </div>
  );
}

function NewsTab({
  status,
  summary,
  sources,
}: {
  status: AgentStatus;
  summary: NewsVisualSummary;
  sources: SourceReference[];
}) {
  if (status !== "completed" && !hasNewsContent(summary)) {
    return <MinimalPending status={status} />;
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 md:grid-cols-5">
        <MetricCard label="Stance" value={summary.stance} />
        <MetricCard label="Sentiment" value={formatNumber(summary.sentiment_score)} />
        <MetricCard label="Positive" value={formatNumber(summary.positive_count)} />
        <MetricCard label="Negative" value={formatNumber(summary.negative_count)} />
        <MetricCard label="Balance" value={balanceLabel(summary)} />
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <ListCard title="Positive" items={summary.positive_points} />
        <ListCard title="Negative" items={summary.negative_points} />
        <ListCard title="Watch" items={summary.watch_items} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <ListCard title="Tailwinds" items={summary.sector_tailwinds} />
        <ListCard title="Headwinds" items={summary.sector_headwinds} />
      </div>
      <SourceSection title="Sources" items={sources} />
    </div>
  );
}

function SummaryBucket({ title, items, emptyLabel }: { title: string; items?: string[]; emptyLabel: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{title}</div>
      <div className="mt-3 space-y-2">
        {items && items.length > 0 ? (
          items.slice(0, 3).map((item) => <div key={item} className="text-sm leading-5 text-slate-100">{item}</div>)
        ) : (
          <div className="text-sm text-slate-400">{emptyLabel}</div>
        )}
      </div>
    </div>
  );
}

function MiniScoreCard({ label, rating }: { label: string; rating?: number | null }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{label}</div>
      <div className="mt-2 text-2xl font-semibold leading-none text-white">{rating ?? "--"}</div>
    </div>
  );
}

function ListCard({ title, items }: { title: string; items?: string[] }) {
  return (
    <section className="rounded-2xl border border-line bg-white p-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{title}</div>
      <div className="mt-3 space-y-2">
        {items && items.length > 0 ? (
          items.slice(0, 4).map((item) => <div key={item} className="text-sm leading-5 text-slate-800">{item}</div>)
        ) : (
          <div className="text-sm text-muted">Pending</div>
        )}
      </div>
    </section>
  );
}

function MetricCard({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <section className="rounded-2xl border border-line bg-slate-50 p-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{label}</div>
      <div className="mt-2 text-base font-semibold text-slate-900">{value ?? "Pending"}</div>
    </section>
  );
}

function MetricPanel({ title, value }: { title: string; value?: string | null }) {
  return (
    <section className="rounded-2xl border border-line bg-white p-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{title}</div>
      <div className="mt-3 text-sm leading-6 text-slate-800">{value || "Pending"}</div>
    </section>
  );
}

function SourceSection({ title, items }: { title: string; items: SourceReference[] }) {
  return (
    <section className="rounded-2xl border border-line bg-white p-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{title}</div>
      <div className="mt-3 grid gap-2">
        {items.length > 0 ? (
          items.map((item) =>
            item.href ? (
              <a
                key={`${item.label}-${item.href}`}
                href={item.href}
                target="_blank"
                rel="noreferrer"
                className="rounded-xl border border-line px-3 py-2 text-sm text-blue-700 hover:bg-slate-50"
              >
                {item.label}
              </a>
            ) : (
              <div key={item.label} className="rounded-xl border border-line px-3 py-2 text-sm text-slate-700">
                {item.label}
              </div>
            ),
          )
        ) : (
          <div className="text-sm text-muted">Pending</div>
        )}
      </div>
    </section>
  );
}

function MinimalPending({ status }: { status: AgentStatus }) {
  return <div className="rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">{minimalStatusCopy(status)}</div>;
}

function StatusPill({ label, tone }: { label: string; tone: "positive" | "caution" | "negative" | "neutral" }) {
  const classes =
    tone === "positive"
      ? "bg-emerald-500/15 text-emerald-200"
      : tone === "caution"
        ? "bg-amber-500/15 text-amber-200"
        : tone === "negative"
          ? "bg-rose-500/15 text-rose-200"
          : "bg-white/10 text-slate-200";
  return <div className={`rounded-full px-3 py-1.5 text-xs font-semibold ${classes}`}>{label}</div>;
}

function buildTimelineSteps(run: SupervisorRun | null): TimelineStep[] {
  return timelineSteps.map((step) => {
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
  });
}

function buildFallbackContributions(run: SupervisorRun) {
  const supervisor = (run.supervisor ?? {}) as SupervisorResult;
  const weights = supervisor.metadata?.weights ?? {};
  return (["fundamental", "technical", "news"] as AgentKey[]).map((name) => ({
    name,
    rating: name === "fundamental" ? run.fundamental?.rating : name === "technical" ? run.technical?.rating : run.news?.rating,
    weight_pct: Math.round(((weights[name] ?? defaultWeight(name)) * 1000)) / 10,
    contribution_pct: undefined,
  }));
}

function defaultWeight(name: AgentKey) {
  if (name === "fundamental") return 0.45;
  if (name === "technical") return 0.3;
  return 0.25;
}

function extractFundamentalSources(worker: WorkerResult): SourceReference[] {
  const rawSources = worker.sources;
  if (!Array.isArray(rawSources)) return [];
  return rawSources.reduce<SourceReference[]>((items, item) => {
    if (!item || typeof item !== "object") return items;
    const record = item as Record<string, unknown>;
    const documentName = readString(record.document_name) ?? "Annual report";
    const pageNumber = typeof record.page_number === "number" ? record.page_number : undefined;
    const headingPath = readString(record.heading_path);
    const parts = [documentName];
    if (pageNumber) parts.push(`Page ${pageNumber}`);
    if (headingPath) parts.push(headingPath);
    items.push({ label: parts.join(" · ") });
    return items;
  }, []);
}

function extractNewsSources(worker: WorkerResult): SourceReference[] {
  const rawSources = worker.sources;
  if (!Array.isArray(rawSources)) return [];
  return rawSources.reduce<SourceReference[]>((items, item) => {
    if (!item || typeof item !== "object") return items;
    const record = item as Record<string, unknown>;
    const title = readString(record.title);
    const href = readString(record.url);
    if (title && href) {
      items.push({ label: title, href });
    }
    return items;
  }, []);
}

function hasFundamentalContent(summary: FundamentalVisualSummary) {
  return Boolean(
    summary.stance ||
      summary.revenue_display ||
      (summary.top_positives && summary.top_positives.length > 0) ||
      (summary.top_risks && summary.top_risks.length > 0),
  );
}

function hasTechnicalContent(summary: TechnicalVisualSummary) {
  return Boolean(
    summary.stance ||
      summary.trend_state ||
      summary.current_price != null ||
      (summary.top_risks && summary.top_risks.length > 0),
  );
}

function hasNewsContent(summary: NewsVisualSummary) {
  return Boolean(
    summary.stance ||
      summary.sentiment_score != null ||
      (summary.positive_points && summary.positive_points.length > 0) ||
      (summary.negative_points && summary.negative_points.length > 0),
  );
}

function balanceLabel(summary: NewsVisualSummary) {
  const positive = summary.positive_count ?? 0;
  const negative = summary.negative_count ?? 0;
  if (positive > negative) return "Positive";
  if (negative > positive) return "Negative";
  return "Mixed";
}

function formatPercent(value?: number | null) {
  if (typeof value !== "number") return undefined;
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function formatNumber(value?: number | null) {
  if (typeof value !== "number") return undefined;
  if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return value.toFixed(Math.abs(value) >= 100 ? 1 : 2).replace(/\.00$/, "");
}

function toneFromRating(rating?: number | null): "positive" | "caution" | "negative" | "neutral" {
  if (typeof rating !== "number") return "neutral";
  if (rating >= 65) return "positive";
  if (rating >= 45) return "caution";
  return "negative";
}

function toneFillClass(tone: "positive" | "caution" | "negative" | "neutral") {
  if (tone === "positive") return "bg-emerald-500";
  if (tone === "caution") return "bg-amber-500";
  if (tone === "negative") return "bg-rose-500";
  return "bg-slate-400";
}

function describeStatus(status: string) {
  if (status === "completed") return "Completed";
  if (status === "running") return "Running";
  if (status === "failed") return "Failed";
  return "Queued";
}

function minimalStatusCopy(status: string) {
  if (status === "completed") return "Ready";
  if (status === "running") return "Running";
  if (status === "failed" || status === "error") return "Failed";
  return "Queued";
}

function readString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function normalizeAgentStatus(status: string | undefined): AgentStatus {
  if (status === "queued") return "idle";
  if (status === "failed") return "error";
  if (status === "running" || status === "completed" || status === "error" || status === "idle") return status;
  return "idle";
}
