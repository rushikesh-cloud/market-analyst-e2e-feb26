import { BarChart3, FileSearch, Newspaper, Route, Sparkles } from "lucide-react";
import type { AgentKey, AgentOutput, ChatMessage, Company, TimelineStep, UploadedDocument, WorkflowRun } from "./types";

export const mockWorkflows: WorkflowRun[] = [
  {
    id: "run-reliance",
    companyName: "Reliance Industries",
    ticker: "RELIANCE.NS",
    sector: "Energy",
    status: "completed",
    finalRating: 74,
    updatedAt: "Today, 10:42",
    agentStatus: { fundamental: "completed", technical: "completed", news: "completed" },
  },
  {
    id: "run-hdfc",
    companyName: "HDFC Bank",
    ticker: "HDFCBANK.NS",
    sector: "Banking",
    status: "running",
    finalRating: undefined,
    updatedAt: "Today, 09:18",
    agentStatus: { fundamental: "completed", technical: "running", news: "idle" },
  },
  {
    id: "run-infosys",
    companyName: "Infosys",
    ticker: "INFY.NS",
    sector: "IT Services",
    status: "completed",
    finalRating: 68,
    updatedAt: "Yesterday",
    agentStatus: { fundamental: "completed", technical: "completed", news: "completed" },
  },
];

export const mockCompanies: Company[] = [
  {
    id: "company-reliance",
    name: "Reliance Industries",
    ticker: "RELIANCE",
    yahooFinanceTicker: "RELIANCE.NS",
    sector: "Energy",
    createdAt: "Today, 10:12",
  },
  {
    id: "company-hdfc",
    name: "HDFC Bank",
    ticker: "HDFCBANK",
    yahooFinanceTicker: "HDFCBANK.NS",
    sector: "Banking",
    createdAt: "Today, 09:06",
  },
  {
    id: "company-infosys",
    name: "Infosys",
    ticker: "INFY",
    yahooFinanceTicker: "INFY.NS",
    sector: "IT Services",
    createdAt: "Yesterday",
  },
];

export const mockUploadedDocuments: UploadedDocument[] = [
  {
    id: "doc-reliance-annual-report",
    companyId: "company-reliance",
    companyName: "Reliance Industries",
    fileName: "reliance-annual-report-2025.pdf",
    fileSize: 4_780_000,
    status: "uploaded",
    uploadedAt: "Today, 10:18",
  },
  {
    id: "doc-infosys-investor-presentation",
    companyId: "company-infosys",
    companyName: "Infosys",
    fileName: "infosys-investor-presentation.pdf",
    fileSize: 2_140_000,
    status: "uploaded",
    uploadedAt: "Yesterday",
  },
];

export const agentOrder: AgentKey[] = ["fundamental", "technical", "news"];

export const baseAgentOutputs: Record<AgentKey, AgentOutput> = {
  fundamental: {
    key: "fundamental",
    title: "Fundamentals",
    status: "idle",
    stream: "",
    evidence: [
      "Revenue growth is steady, with improved operating leverage.",
      "Debt profile is manageable against cash-flow generation.",
      "Management commentary remains expansion-focused.",
    ],
    details: {
      Growth: "Strong demand and margin discipline support a positive base case.",
      Debt: "Leverage is visible but not thesis-breaking.",
      Cash: "Operating cash flow covers near-term reinvestment needs.",
    },
  },
  technical: {
    key: "technical",
    title: "Technical",
    status: "idle",
    stream: "",
    evidence: [
      "Price remains above the 50-day moving average.",
      "RSI is firm without entering extreme overbought territory.",
      "MACD slope supports near-term momentum.",
    ],
    details: {
      Trend: "Constructive medium-term trend.",
      Momentum: "Positive but watch for exhaustion near resistance.",
      "Support / Resistance": "Support near the last consolidation band; resistance near recent highs.",
    },
  },
  news: {
    key: "news",
    title: "News",
    status: "idle",
    stream: "",
    evidence: [
      "Recent coverage is net favorable with sector demand tailwinds.",
      "Adverse items are mainly valuation and execution-risk related.",
      "Watch items include policy, rates, and peer guidance.",
    ],
    details: {
      Favorable: ["Demand recovery", "Strategic investment", "Sector rotation support"],
      Adverse: ["High expectations", "Input-cost risk"],
      Watch: ["Next earnings call", "Regulatory updates", "Peer commentary"],
    },
  },
};

export const timelineSteps: TimelineStep[] = [
  { id: "prompt", label: "Prompt", status: "completed", icon: Route },
  { id: "fundamental", label: "Fundamental", status: "idle", icon: FileSearch },
  { id: "technical", label: "Technical", status: "idle", icon: BarChart3 },
  { id: "news", label: "News", status: "idle", icon: Newspaper },
  { id: "supervisor", label: "Supervisor", status: "idle", icon: Sparkles },
];

export const mockChatMessages: ChatMessage[] = [
  {
    id: "m1",
    role: "assistant",
    content: "The supervisor result is ready. Ask a follow-up about fundamentals, technicals, news, or the final rating.",
  },
];
