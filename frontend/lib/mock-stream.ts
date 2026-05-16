import type { AgentKey, RunEvent } from "./types";

const chunks: Record<AgentKey, string[]> = {
  fundamental: [
    "Scanning annual-report context for growth, debt, cash flow, and management commentary. ",
    "Evidence suggests durable demand with controlled leverage. ",
    "Assigning a constructive fundamental rating from the retrieved context.",
  ],
  technical: [
    "Generating price chart with moving averages, RSI, and MACD. ",
    "Chart shows price holding above the medium-term trend line. ",
    "Momentum is positive, with resistance near the recent high.",
  ],
  news: [
    "Searching company and sector news for favorable and adverse developments. ",
    "Recent items lean positive, but valuation sensitivity remains a watch item. ",
    "Source-attributed news context supports a moderately positive score.",
  ],
};

const ratings: Record<AgentKey, number> = {
  fundamental: 78,
  technical: 71,
  news: 67,
};

export function buildMockRunEvents(): RunEvent[] {
  let at = 250;
  const events: RunEvent[] = [{ type: "run_started", at }];

  (["fundamental", "technical", "news"] as AgentKey[]).forEach((agent) => {
    at += 650;
    events.push({ type: "agent_started", at, agent });
    chunks[agent].forEach((content) => {
      at += 900;
      events.push({ type: "agent_chunk", at, agent, content });
      if (agent === "technical" && content.includes("Chart shows")) {
        events.push({ type: "chart_ready", at: at + 150 });
      }
    });
    at += 650;
    events.push({ type: "agent_completed", at, agent, rating: ratings[agent] });
  });

  at += 700;
  events.push({ type: "supervisor_started", at });
  at += 900;
  events.push({
    type: "supervisor_chunk",
    at,
    content: "Combining worker ratings with weights: fundamentals 45%, technicals 30%, news 25%. ",
  });
  at += 900;
  events.push({
    type: "supervisor_chunk",
    at,
    content: "The result is positive but not aggressive; upside depends on execution and sustained momentum.",
  });
  at += 650;
  events.push({ type: "supervisor_completed", at, rating: 73 });

  return events;
}

export function subscribeToMockRun(onEvent: (event: RunEvent) => void) {
  const timers = buildMockRunEvents().map((event) => window.setTimeout(() => onEvent(event), event.at));
  return () => timers.forEach(window.clearTimeout);
}
