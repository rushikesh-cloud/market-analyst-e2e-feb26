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

export type FundamentalVisualSummary = {
  stance?: string | null;
  revenue_display?: string | null;
  revenue_growth_pct?: number | null;
  profit_margin_pct?: number | null;
  debt_to_equity?: number | null;
  cash_flow_view?: string | null;
  valuation_view?: string | null;
  top_positives?: string[];
  top_risks?: string[];
  watch_items?: string[];
};

export type TechnicalVisualSummary = {
  stance?: string | null;
  trend_state?: string | null;
  momentum_state?: string | null;
  setup?: string | null;
  current_price?: number | null;
  rsi?: number | null;
  distance_to_ma20_pct?: number | null;
  distance_to_ma50_pct?: number | null;
  macd_signal_state?: string | null;
  support_levels?: string[];
  resistance_levels?: string[];
  top_risks?: string[];
  watch_items?: string[];
};

export type NewsVisualSummary = {
  stance?: string | null;
  sentiment_score?: number | null;
  positive_count?: number | null;
  negative_count?: number | null;
  positive_points?: string[];
  negative_points?: string[];
  sector_tailwinds?: string[];
  sector_headwinds?: string[];
  watch_items?: string[];
};

export type SupervisorVisualComponent = {
  name: string;
  rating?: number | null;
  weight_pct: number;
  contribution_pct?: number | null;
};

export type SupervisorVisualSummary = {
  stance?: string | null;
  confidence?: string | null;
  decision?: string | null;
  top_positives?: string[];
  top_risks?: string[];
  watch_items?: string[];
  component_contributions?: SupervisorVisualComponent[];
};

export type WorkerResult = {
  answer?: string;
  rating?: number | null;
  question?: string;
  ticker?: string | null;
  company_name?: string;
  sector?: string | null;
  chart_path?: string | null;
  structured_output?: Record<string, unknown>;
  visual_summary?: FundamentalVisualSummary | TechnicalVisualSummary | NewsVisualSummary | null;
  [key: string]: unknown;
};

export type SupervisorResult = {
  final_rating?: number;
  summary?: string;
  components?: Array<{ name: string; rating?: number | null; weight: number; rationale: string }>;
  metadata?: { weights?: Partial<Record<AgentKey, number>> };
  visual_summary?: SupervisorVisualSummary | null;
  structured_output?: Record<string, unknown>;
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
