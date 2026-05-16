"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Building2, Plus, Save, Search, X } from "lucide-react";
import { readStoredList, writeStoredList } from "@/lib/client-store";
import { mockCompanies } from "@/lib/mock-data";
import type { Company, CompanyDraft } from "@/lib/types";

const STORAGE_KEY = "market-analyst:companies";

const emptyDraft: CompanyDraft = {
  name: "",
  ticker: "",
  yahooFinanceTicker: "",
  sector: "",
};

export function CompanyDirectory() {
  const [companies, setCompanies] = useState<Company[]>(mockCompanies);
  const [draft, setDraft] = useState<CompanyDraft>(emptyDraft);
  const [query, setQuery] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    setCompanies(readStoredList(STORAGE_KEY, mockCompanies));
  }, []);

  function update(field: keyof CompanyDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function saveCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextCompany: Company = {
      id: `company-${draft.ticker.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`,
      name: draft.name.trim(),
      ticker: draft.ticker.trim().toUpperCase(),
      yahooFinanceTicker: draft.yahooFinanceTicker.trim().toUpperCase(),
      sector: draft.sector.trim(),
      createdAt: "Just now",
    };
    const nextCompanies = [nextCompany, ...companies];
    setCompanies(nextCompanies);
    writeStoredList(STORAGE_KEY, nextCompanies);
    setDraft(emptyDraft);
    setIsAdding(false);
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
              onClick={() => setIsAdding((current) => !current)}
              className="flex h-9 items-center justify-center gap-2 rounded-lg bg-ink px-3 text-sm font-semibold text-white"
            >
              {isAdding ? <X size={15} /> : <Plus size={15} />}
              {isAdding ? "Close" : "Add company"}
            </button>
          </div>
        </div>

        {isAdding ? (
          <form onSubmit={saveCompany} className="grid gap-3 border-b border-line bg-slate-50 p-4 md:grid-cols-2 xl:grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr_auto] xl:items-end">
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
            <button type="submit" className="flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white">
              <Save size={15} />
              Save
            </button>
          </form>
        ) : null}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead className="border-b border-line bg-slate-50 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
              <tr>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Ticker</th>
                <th className="px-4 py-3">Yahoo Finance</th>
                <th className="px-4 py-3">Sector</th>
                <th className="px-4 py-3">Added</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
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
                  <td className="px-4 py-3 text-xs text-muted">{company.createdAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
