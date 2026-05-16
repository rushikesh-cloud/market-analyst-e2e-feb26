import type { Company, CompanyDraft, CompanyUpdateDraft, UploadedDocument } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed with ${response.status}`);
  }
  return (await response.json()) as T;
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
