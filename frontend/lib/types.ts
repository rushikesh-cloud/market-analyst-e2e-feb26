import type { LucideIcon } from "lucide-react";

export type AgentKey = "fundamental" | "technical" | "news";
export type RunStatus = "queued" | "running" | "completed" | "failed" | "error";
export type AgentStatus = "idle" | "running" | "completed" | "failed" | "error";

export type SupervisorRun = {
  id: string;
  companyId: string;
  companyName: string;
  ticker: string;
  yahooFinanceTicker?: string | null;
  sector?: string;
  documentId: string;
  documentName: string;
  documentStatus: string;
  status: RunStatus;
  errorMessage?: string | null;
  finalRating?: number;
  fundamentalStatus: AgentStatus;
  technicalStatus: AgentStatus;
  newsStatus: AgentStatus;
  fundamental?: WorkerResult | null;
  technical?: WorkerResult | null;
  news?: WorkerResult | null;
  supervisor?: SupervisorResult | null;
  createdAt: string;
  updatedAt: string;
};

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
  companyId: string;
  documentId: string;
};

export type Company = {
  id: string;
  name: string;
  ticker: string;
  yahooFinanceTicker: string;
  sector: string;
  overallScore?: number | null;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type CompanyDraft = {
  name: string;
  ticker: string;
  yahooFinanceTicker: string;
  sector: string;
  status?: string;
  overallScore?: number | null;
};

export type CompanyUpdateDraft = CompanyDraft & {
  status: string;
  overallScore?: number | null;
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
  stageHistory?: DocumentStageHistoryEntry[];
  uploadedAt: string;
  updatedAt?: string;
};

export type DocumentStageHistoryEntry = {
  stage: "stored" | "extracting_markdown" | "chunking" | "embedding" | "syncing_reports" | "completed" | "failed";
  status: "completed" | "running" | "upcoming" | "failed";
  startedAt?: string | null;
  completedAt?: string | null;
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
  sources: SourceReference[];
  chartUrl?: string;
  details: Record<string, string | string[]>;
  status: AgentStatus;
};

export type SourceReference = {
  label: string;
  href?: string;
};

export type WorkerResult = {
  answer?: string;
  rating?: number | null;
  question?: string;
  ticker?: string | null;
  company_name?: string;
  sector?: string | null;
  chart_path?: string | null;
  [key: string]: unknown;
};

export type SupervisorResult = {
  final_rating?: number;
  summary?: string;
  components?: Array<{ name: string; rating?: number | null; weight: number; rationale: string }>;
  metadata?: { weights?: Partial<Record<AgentKey, number>> };
  [key: string]: unknown;
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

export type AuthUser = {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  mobileNumber: string;
  gender: string;
  dob: string;
  createdAt: string;
  updatedAt: string;
};

export type AuthLoginDraft = {
  email: string;
  password: string;
};

export type AuthRegisterDraft = {
  firstName: string;
  lastName: string;
  email: string;
  mobileNumber: string;
  gender: string;
  dob: string;
  password: string;
  confirmPassword: string;
};

export type SupervisorRunChatRequest = {
  message: string;
  history: Array<Pick<ChatMessage, "role" | "content">>;
  maxHistoryMessages?: number;
};

export type SupervisorRunChatResponse = {
  answer: string;
  history: Array<Pick<ChatMessage, "role" | "content">>;
  toolNames: string[];
};

export type SupervisorRunChatStreamEvent =
  | { type: "token"; content: string }
  | { type: "final"; answer: string; history: Array<Pick<ChatMessage, "role" | "content">>; toolNames: string[] }
  | { type: "error"; message: string };

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
