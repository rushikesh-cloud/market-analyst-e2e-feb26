"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { FileText, FileUp, Plus, Send, X } from "lucide-react";
import { listCompanies, listDocuments, uploadDocument } from "@/lib/api";
import type { Company, UploadedDocument } from "@/lib/types";

function formatBytes(bytes: number) {
  if (bytes < 1_000_000) return `${Math.max(1, Math.round(bytes / 1_000))} KB`;
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}

export function DocumentLibrary() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [companyId, setCompanyId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    Promise.all([listCompanies(), listDocuments()])
      .then(([companyItems, documentItems]) => {
        if (!isMounted) return;
        setCompanies(companyItems);
        setCompanyId((current) => current || companyItems[0]?.id || "");
        setDocuments(documentItems);
      })
      .catch((apiError: unknown) => {
        if (isMounted) setError(apiError instanceof Error ? apiError.message : "Unable to load documents");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!documents.some((document) => document.status === "processing" || document.status === "uploaded")) return;
    const intervalId = window.setInterval(() => {
      listDocuments()
        .then(setDocuments)
        .catch((apiError: unknown) => setError(apiError instanceof Error ? apiError.message : "Unable to refresh document status"));
    }, 3000);
    return () => window.clearInterval(intervalId);
  }, [documents]);

  const companyById = useMemo(() => new Map(companies.map((company) => [company.id, company])), [companies]);

  async function submitDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;

    const company = companyById.get(companyId);
    if (!company) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const nextDocument = await uploadDocument(company.id, file);
      setDocuments((current) => [nextDocument, ...current.filter((document) => document.id !== nextDocument.id)]);
      setFile(null);
      setIsAdding(false);
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Unable to submit document");
    } finally {
      setIsSubmitting(false);
    }
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
                {companies.length === 0 ? <option value="">No companies available</option> : null}
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
            <button
              type="submit"
              disabled={isSubmitting || companies.length === 0}
              className="flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Send size={15} />
              {isSubmitting ? "Submitting" : "Submit"}
            </button>
          </form>
        ) : null}

        {error ? <div className="border-b border-line bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div> : null}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[920px] border-collapse text-left">
            <thead className="border-b border-line bg-slate-50 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
              <tr>
                <th className="px-4 py-3">Document</th>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Progress</th>
                <th className="px-4 py-3">Uploaded</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {isLoading ? (
                <tr>
                  <td className="px-4 py-5 text-sm text-muted" colSpan={6}>
                    Loading documents...
                  </td>
                </tr>
              ) : null}
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
                    <span className={`rounded-md border px-2 py-1 text-xs font-medium ${statusClassName(document.status)}`}>
                      {document.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">
                    <div>{formatStage(document.stage)}</div>
                    <div>
                      {document.pageCount ? `${document.pagesProcessed ?? document.pageCount}/${document.pageCount} pages` : "Pages pending"}
                      {document.chunkCount ? `, ${document.chunkCount} chunks` : ""}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">{formatDate(document.uploadedAt)}</td>
                </tr>
              ))}
              {!isLoading && documents.length === 0 ? (
                <tr>
                  <td className="px-4 py-5 text-sm text-muted" colSpan={6}>
                    No documents uploaded.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatStage(stage: UploadedDocument["stage"]) {
  if (!stage) return "Pending";
  return stage.replaceAll("_", " ");
}

function statusClassName(status: UploadedDocument["status"]) {
  if (status === "completed") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "failed") return "border-red-200 bg-red-50 text-red-700";
  if (status === "processing") return "border-blue-200 bg-blue-50 text-blue-700";
  return "border-slate-200 bg-slate-50 text-slate-700";
}
