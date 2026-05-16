"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { FileText, FileUp, Plus, Send, X } from "lucide-react";
import { readStoredList, writeStoredList } from "@/lib/client-store";
import { mockCompanies, mockUploadedDocuments } from "@/lib/mock-data";
import type { Company, UploadedDocument } from "@/lib/types";

const COMPANY_STORAGE_KEY = "market-analyst:companies";
const DOCUMENT_STORAGE_KEY = "market-analyst:documents";

function formatBytes(bytes: number) {
  if (bytes < 1_000_000) return `${Math.max(1, Math.round(bytes / 1_000))} KB`;
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}

export function DocumentLibrary() {
  const [companies, setCompanies] = useState<Company[]>(mockCompanies);
  const [documents, setDocuments] = useState<UploadedDocument[]>(mockUploadedDocuments);
  const [isAdding, setIsAdding] = useState(false);
  const [companyId, setCompanyId] = useState(mockCompanies[0]?.id ?? "");
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    const storedCompanies = readStoredList(COMPANY_STORAGE_KEY, mockCompanies);
    setCompanies(storedCompanies);
    setCompanyId((current) => current || storedCompanies[0]?.id || "");
    setDocuments(readStoredList(DOCUMENT_STORAGE_KEY, mockUploadedDocuments));
  }, []);

  const companyById = useMemo(() => new Map(companies.map((company) => [company.id, company])), [companies]);

  function submitDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;

    const company = companyById.get(companyId);
    if (!company) return;

    const nextDocument: UploadedDocument = {
      id: `doc-${company.id}-${Date.now()}`,
      companyId: company.id,
      companyName: company.name,
      fileName: file.name,
      fileSize: file.size,
      status: "submitted",
      uploadedAt: "Just now",
    };
    const nextDocuments = [nextDocument, ...documents];
    setDocuments(nextDocuments);
    writeStoredList(DOCUMENT_STORAGE_KEY, nextDocuments);
    setFile(null);
    setIsAdding(false);
  }

  return (
    <div className="grid gap-5 p-4 md:p-6">
      <section className="rounded-xl border border-line bg-panel shadow-soft">
        <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-base font-semibold">Documents</h1>
            <p className="mt-0.5 text-xs text-muted">Upload company documents for fundamental analysis and RAG ingestion.</p>
          </div>
          <button
            type="button"
            onClick={() => setIsAdding((current) => !current)}
            className="flex h-9 items-center justify-center gap-2 rounded-lg bg-ink px-3 text-sm font-semibold text-white"
          >
            {isAdding ? <X size={15} /> : <Plus size={15} />}
            {isAdding ? "Close" : "Add document"}
          </button>
        </div>

        {isAdding ? (
          <form onSubmit={submitDocument} className="grid gap-3 border-b border-line bg-slate-50 p-4 md:grid-cols-[minmax(220px,320px)_1fr_auto] md:items-end">
            <label className="grid gap-1.5 text-xs font-medium text-muted">
              Company
              <select
                value={companyId}
                onChange={(event) => setCompanyId(event.target.value)}
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-ink outline-none"
                required
              >
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1.5 text-xs font-medium text-muted">
              Document
              <span className="flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-dashed border-line bg-white px-3 text-sm text-ink">
                <FileUp size={15} className="text-muted" />
                <span className="min-w-0 flex-1 truncate">{file?.name ?? "Select PDF or company document"}</span>
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  className="sr-only"
                  required
                />
              </span>
            </label>
            <button type="submit" className="flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white">
              <Send size={15} />
              Submit
            </button>
          </form>
        ) : null}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead className="border-b border-line bg-slate-50 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
              <tr>
                <th className="px-4 py-3">Document</th>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Uploaded</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {documents.map((document) => (
                <tr key={document.id} className="transition hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-white text-muted">
                        <FileText size={15} />
                      </span>
                      <span className="max-w-[320px] truncate text-sm font-semibold">{document.fileName}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-ink">{document.companyName}</td>
                  <td className="px-4 py-3 text-sm text-muted">{formatBytes(document.fileSize)}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                      {document.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">{document.uploadedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
