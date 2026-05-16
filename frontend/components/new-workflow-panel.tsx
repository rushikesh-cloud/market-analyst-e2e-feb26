"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Play } from "lucide-react";
import { createSupervisorRun, listCompanies, listDocuments } from "@/lib/api";
import type { Company, NewWorkflowDraft, UploadedDocument } from "@/lib/types";


export function NewWorkflowPanel() {
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [draft, setDraft] = useState<NewWorkflowDraft>({
    companyId: "",
    documentId: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    Promise.all([listCompanies(), listDocuments()])
      .then(([companyItems, documentItems]) => {
        if (!isMounted) return;
        setCompanies(companyItems);
        setDocuments(documentItems);
        const firstCompanyId = companyItems[0]?.id ?? "";
        const firstDocumentId = documentItems.find((item) => item.companyId === firstCompanyId && item.status === "completed")?.id ?? "";
        setDraft({ companyId: firstCompanyId, documentId: firstDocumentId });
      })
      .catch((apiError: unknown) => {
        if (isMounted) setError(apiError instanceof Error ? apiError.message : "Unable to load workflow inputs");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const availableDocuments = useMemo(
    () => documents.filter((item) => item.companyId === draft.companyId),
    [documents, draft.companyId],
  );
  const completedDocuments = availableDocuments.filter((item) => item.status === "completed");

  function updateCompany(companyId: string) {
    const nextDocumentId = documents.find((item) => item.companyId === companyId && item.status === "completed")?.id ?? "";
    setDraft({ companyId, documentId: nextDocumentId });
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.companyId || !draft.documentId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const run = await createSupervisorRun(draft.companyId, draft.documentId);
      router.push(`/runs/${run.id}`);
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Unable to start supervisor workflow");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-xl border border-line bg-panel shadow-soft">
      <div className="border-b border-line p-4">
        <h2 className="text-sm font-semibold">New Workflow</h2>
        <p className="mt-0.5 text-xs text-muted">Start a supervisor run from an existing company and a completed document.</p>
      </div>
      <form onSubmit={submit} className="grid gap-3 p-4">
        <label className="grid gap-1.5 text-xs font-medium text-muted">
          Company
          <select
            value={draft.companyId}
            onChange={(event) => updateCompany(event.target.value)}
            className="h-10 rounded-lg border border-line px-3 text-sm text-ink outline-none"
            disabled={isLoading || isSubmitting}
            required
          >
            <option value="">{isLoading ? "Loading companies..." : "Select company"}</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name} ({company.yahooFinanceTicker})
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1.5 text-xs font-medium text-muted">
          Document
          <select
            value={draft.documentId}
            onChange={(event) => setDraft((current) => ({ ...current, documentId: event.target.value }))}
            className="h-10 rounded-lg border border-line px-3 text-sm text-ink outline-none"
            disabled={isLoading || isSubmitting || !draft.companyId}
            required
          >
            <option value="">
              {draft.companyId ? (completedDocuments.length > 0 ? "Select completed document" : "No completed documents for this company") : "Select company first"}
            </option>
            {completedDocuments.map((document) => (
              <option key={document.id} value={document.id}>
                {document.documentName ?? document.fileName}
              </option>
            ))}
          </select>
        </label>
        {availableDocuments.some((item) => item.status !== "completed") ? (
          <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            Only documents with completed ingestion can start a supervisor run.
          </div>
        ) : null}
        {error ? <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div> : null}
        <button
          type="submit"
          disabled={isLoading || isSubmitting || !draft.companyId || !draft.documentId}
          className="mt-1 flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Play size={15} fill="currentColor" />
          {isSubmitting ? "Starting" : "Start supervisor run"}
        </button>
      </form>
    </section>
  );
}
