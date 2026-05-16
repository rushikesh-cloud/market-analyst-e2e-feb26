"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Building2, Pencil, Plus, Save, Search, X } from "lucide-react";
import { createCompany, listCompanies, updateCompany } from "@/lib/api";
import type { Company, CompanyDraft, CompanyUpdateDraft } from "@/lib/types";

const emptyDraft: CompanyDraft = {
  name: "",
  ticker: "",
  yahooFinanceTicker: "",
  sector: "",
};

type CompanyFormDraft = {
  name: string;
  ticker: string;
  yahooFinanceTicker: string;
  sector: string;
  status: string;
  overallScore: string;
};

const emptyFormDraft: CompanyFormDraft = {
  ...emptyDraft,
  status: "pending",
  overallScore: "",
};

export function CompanyDirectory() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [draft, setDraft] = useState<CompanyFormDraft>(emptyFormDraft);
  const [query, setQuery] = useState("");
  const [editingCompanyId, setEditingCompanyId] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    listCompanies()
      .then((items) => {
        if (isMounted) setCompanies(items);
      })
      .catch((apiError: unknown) => {
        if (isMounted) setError(apiError instanceof Error ? apiError.message : "Unable to load companies");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  function update(field: keyof CompanyFormDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function openAddForm() {
    setDraft(emptyFormDraft);
    setEditingCompanyId(null);
    setIsFormOpen(true);
    setError(null);
  }

  function closeForm() {
    setDraft(emptyFormDraft);
    setEditingCompanyId(null);
    setIsFormOpen(false);
  }

  function openEditForm(company: Company) {
    setDraft({
      name: company.name,
      ticker: company.ticker,
      yahooFinanceTicker: company.yahooFinanceTicker,
      sector: company.sector ?? "",
      status: company.status,
      overallScore: company.overallScore == null ? "" : String(company.overallScore),
    });
    setEditingCompanyId(company.id);
    setIsFormOpen(true);
    setError(null);
  }

  async function saveCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      const nextOverallScore = draft.overallScore.trim() === "" ? null : Number(draft.overallScore);
      if (draft.overallScore.trim() !== "" && Number.isNaN(nextOverallScore)) {
        throw new Error("Overall score must be a number");
      }

      const nextCompany =
        editingCompanyId == null
          ? await createCompany({
              name: draft.name,
              ticker: draft.ticker,
              yahooFinanceTicker: draft.yahooFinanceTicker,
              sector: draft.sector,
              status: draft.status,
              overallScore: nextOverallScore,
            })
          : await updateCompany(editingCompanyId, {
              name: draft.name,
              ticker: draft.ticker,
              yahooFinanceTicker: draft.yahooFinanceTicker,
              sector: draft.sector,
              status: draft.status,
              overallScore: nextOverallScore,
            } satisfies CompanyUpdateDraft);

      setCompanies((current) => {
        if (editingCompanyId == null) {
          return [nextCompany, ...current.filter((company) => company.id !== nextCompany.id)];
        }
        return current.map((company) => (company.id === nextCompany.id ? nextCompany : company));
      });
      closeForm();
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Unable to save company");
    } finally {
      setIsSaving(false);
    }
  }

  const visibleCompanies = companies.filter((company) => {
    const haystack = `${company.name} ${company.ticker} ${company.yahooFinanceTicker} ${company.sector}`.toLowerCase();
    return haystack.includes(query.toLowerCase());
  });

  return (
    <div className="grid gap-5 p-4 md:p-6">
      <section className="rounded-xl border border-line bg-panel shadow-soft">
        <div className="flex flex-col gap-3 border-b border-line p-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-base font-semibold">Companies</h1>
            <p className="mt-0.5 text-xs text-muted">Manage company master data for workflow and document selection.</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="flex h-9 min-w-0 items-center gap-2 rounded-lg border border-line bg-white px-3 text-xs text-muted sm:w-72">
              <Search size={15} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search companies"
                className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-muted"
              />
            </label>
            <button
              type="button"
              onClick={() => (isFormOpen ? closeForm() : openAddForm())}
              className="flex h-9 items-center justify-center gap-2 rounded-lg bg-ink px-3 text-sm font-semibold text-white"
            >
              {isFormOpen ? <X size={15} /> : <Plus size={15} />}
              {isFormOpen ? "Close" : "Add company"}
            </button>
          </div>
        </div>

        {isFormOpen ? (
          <form
            onSubmit={saveCompany}
            className="grid gap-3 border-b border-line bg-slate-50 p-4 md:grid-cols-2 xl:grid-cols-[1.2fr_0.8fr_0.9fr_0.9fr_0.8fr_0.7fr_auto] xl:items-end"
          >
            <label className="grid gap-1.5 text-xs font-medium text-muted">
              Company name
              <input
                value={draft.name}
                onChange={(event) => update("name", event.target.value)}
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-ink outline-none"
                required
              />
            </label>
            <label className="grid gap-1.5 text-xs font-medium text-muted">
              Ticker
              <input
                value={draft.ticker}
                onChange={(event) => update("ticker", event.target.value.toUpperCase())}
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-ink outline-none"
                required
              />
            </label>
            <label className="grid gap-1.5 text-xs font-medium text-muted">
              Yahoo Finance ticker
              <input
                value={draft.yahooFinanceTicker}
                onChange={(event) => update("yahooFinanceTicker", event.target.value.toUpperCase())}
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-ink outline-none"
                required
              />
            </label>
            <label className="grid gap-1.5 text-xs font-medium text-muted">
              Sector
              <input
                value={draft.sector}
                onChange={(event) => update("sector", event.target.value)}
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-ink outline-none"
                required
              />
            </label>
            <label className="grid gap-1.5 text-xs font-medium text-muted">
              Status
              <input
                value={draft.status}
                onChange={(event) => update("status", event.target.value)}
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-ink outline-none"
                required
              />
            </label>
            <label className="grid gap-1.5 text-xs font-medium text-muted">
              Overall score
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                value={draft.overallScore}
                onChange={(event) => update("overallScore", event.target.value)}
                className="h-10 rounded-lg border border-line bg-white px-3 text-sm text-ink outline-none"
                placeholder="Optional"
              />
            </label>
            <button
              type="submit"
              disabled={isSaving}
              className="flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Save size={15} />
              {isSaving ? "Saving" : editingCompanyId == null ? "Save" : "Update"}
            </button>
          </form>
        ) : null}

        {error ? <div className="border-b border-line bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div> : null}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] border-collapse text-left">
            <thead className="border-b border-line bg-slate-50 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
              <tr>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Ticker</th>
                <th className="px-4 py-3">Yahoo Finance</th>
                <th className="px-4 py-3">Sector</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Overall Score</th>
                <th className="px-4 py-3">Added</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {isLoading ? (
                <tr>
                  <td className="px-4 py-5 text-sm text-muted" colSpan={8}>
                    Loading companies...
                  </td>
                </tr>
              ) : null}
              {visibleCompanies.map((company) => (
                <tr key={company.id} className="transition hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-white text-muted">
                        <Building2 size={15} />
                      </span>
                      <span className="text-sm font-semibold">{company.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-ink">{company.ticker}</td>
                  <td className="px-4 py-3 text-sm text-ink">{company.yahooFinanceTicker}</td>
                  <td className="px-4 py-3 text-sm text-muted">{company.sector}</td>
                  <td className="px-4 py-3 text-sm text-muted">{company.status}</td>
                  <td className="px-4 py-3 text-sm text-muted">{formatScore(company.overallScore)}</td>
                  <td className="px-4 py-3 text-xs text-muted">{formatDate(company.createdAt)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => openEditForm(company)}
                      className="inline-flex h-8 items-center justify-center gap-1 rounded-lg border border-line bg-white px-3 text-xs font-medium text-ink transition hover:bg-slate-50"
                    >
                      <Pencil size={13} />
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
              {!isLoading && visibleCompanies.length === 0 ? (
                <tr>
                  <td className="px-4 py-5 text-sm text-muted" colSpan={8}>
                    No companies found.
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

function formatScore(value?: number | null) {
  if (value == null) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
