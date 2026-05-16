import type {
  AuthLoginDraft,
  AuthRegisterDraft,
  AuthUser,
  Company,
  CompanyDraft,
  CompanyUpdateDraft,
  SupervisorRun,
  SupervisorRunChatRequest,
  SupervisorRunChatResponse,
  UploadedDocument,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new ApiError(response.status, message || `API request failed with ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function buildGoogleAuthStartUrl(nextPath: string = "/"): string {
  const suffix = `?next=${encodeURIComponent(nextPath.startsWith("/") ? nextPath : "/")}`;
  return `${API_BASE_URL}/api/auth/google/start${suffix}`;
}

export function startGoogleAuth(nextPath: string = "/") {
  window.location.assign(buildGoogleAuthStartUrl(nextPath));
}

export function registerUser(draft: AuthRegisterDraft): Promise<AuthUser> {
  return request<AuthUser>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(draft),
  });
}

export function loginUser(draft: AuthLoginDraft): Promise<AuthUser> {
  return request<AuthUser>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(draft),
  });
}

export function getCurrentUser(): Promise<AuthUser> {
  return request<AuthUser>("/api/auth/me");
}

export function logoutUser(): Promise<void> {
  return request<void>("/api/auth/logout", { method: "POST" });
}

export function listCompanies(): Promise<Company[]> {
  return request<Company[]>("/api/companies");
}

export function createCompany(draft: CompanyDraft): Promise<Company> {
  return request<Company>("/api/companies", {
    method: "POST",
    body: JSON.stringify(draft),
  });
}

export function updateCompany(companyId: string, draft: CompanyUpdateDraft): Promise<Company> {
  return request<Company>(`/api/companies/${companyId}`, {
    method: "PUT",
    body: JSON.stringify(draft),
  });
}

export function listDocuments(companyId?: string): Promise<UploadedDocument[]> {
  const suffix = companyId ? `?companyId=${encodeURIComponent(companyId)}` : "";
  return request<UploadedDocument[]>(`/api/documents${suffix}`);
}

export function uploadDocument(companyId: string, file: File): Promise<UploadedDocument> {
  const formData = new FormData();
  formData.append("companyId", companyId);
  formData.append("file", file);
  return request<UploadedDocument>("/api/documents", {
    method: "POST",
    body: formData,
  });
}

export function listSupervisorRuns(): Promise<SupervisorRun[]> {
  return request<SupervisorRun[]>("/api/supervisor-runs");
}

export function getSupervisorRun(runId: string): Promise<SupervisorRun> {
  return request<SupervisorRun>(`/api/supervisor-runs/${runId}`);
}

export function getSupervisorRunTechnicalChartUrl(runId: string): string {
  return `${API_BASE_URL}/api/supervisor-runs/${runId}/technical-chart`;
}

export function createSupervisorRun(companyId: string, documentId: string): Promise<SupervisorRun> {
  return request<SupervisorRun>("/api/supervisor-runs", {
    method: "POST",
    body: JSON.stringify({ companyId, documentId }),
  });
}

export function chatWithSupervisorRun(runId: string, payload: SupervisorRunChatRequest): Promise<SupervisorRunChatResponse> {
  return request<SupervisorRunChatResponse>(`/api/supervisor-runs/${runId}/chat`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
