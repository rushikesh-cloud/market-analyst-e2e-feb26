import type { LucideIcon } from "lucide-react";

export type AgentKey = "fundamental" | "technical" | "news";
export type RunStatus = "queued" | "running" | "completed" | "error";
export type AgentStatus = "idle" | "running" | "completed" | "error";

export type WorkflowRun = {
  id: string;
  companyName: string;
  ticker: string;
  sector?: string;
  status: RunStatus;
  finalRating?: number;
  updatedAt: string;
  agentStatus: Record<AgentKey, AgentStatus>;
};

export type NewWorkflowDraft = {
  companyName: string;
  ticker: string;
  sector?: string;
};

export type Company = {
  id: string;
  name: string;
  ticker: string;
  yahooFinanceTicker: string;
  sector: string;
  createdAt: string;
};

export type CompanyDraft = {
  name: string;
  ticker: string;
  yahooFinanceTicker: string;
  sector: string;
};

export type UploadedDocument = {
  id: string;
  companyId: string;
  companyName: string;
  documentName?: string;
  fileName: string;
  fileSize: number;
  status: "uploaded" | "processing" | "completed" | "failed";
  stage?: "stored" | "extracting_markdown" | "chunking" | "embedding" | "syncing_reports" | "completed" | "failed";
  pageCount?: number | null;
  pagesProcessed?: number | null;
  chunkCount?: number | null;
  vectorIdsCount?: number | null;
  reportsRows?: number | null;
  errorMessage?: string | null;
  uploadedAt: string;
  updatedAt?: string;
};

export type TimelineStep = {
  id: string;
  label: string;
  status: AgentStatus;
  icon?: LucideIcon;
};

export type AgentOutput = {
  key: AgentKey;
  title: string;
  rating?: number;
  stream: string;
  evidence: string[];
  details: Record<string, string | string[]>;
  status: AgentStatus;
};

export type SupervisorOutput = {
  rating?: number;
  status: AgentStatus;
  summary: string;
  weights: Record<AgentKey, number>;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export type RunEvent =
  | { type: "run_started"; at: number }
  | { type: "agent_started"; at: number; agent: AgentKey }
  | { type: "agent_chunk"; at: number; agent: AgentKey; content: string }
  | { type: "chart_ready"; at: number }
  | { type: "agent_completed"; at: number; agent: AgentKey; rating: number }
  | { type: "supervisor_started"; at: number }
  | { type: "supervisor_chunk"; at: number; content: string }
  | { type: "supervisor_completed"; at: number; rating: number }
  | { type: "error"; at: number; message: string; agent?: AgentKey };
