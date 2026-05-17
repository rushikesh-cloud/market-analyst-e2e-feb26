"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Bot, Building2, FileText, History, LogOut, Plus, Settings } from "lucide-react";
import type { ReactNode } from "react";
import { RequireAuth, useAuth } from "@/components/auth-provider";

const navItems = [
  { label: "Workflows", href: "/", icon: History },
  { label: "Companies", href: "/companies", icon: Building2 },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "New", href: "/?new=1", icon: Plus },
  { label: "Agents", href: "/agents", icon: Bot },
  { label: "Settings", href: "/#settings", icon: Settings },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <RequireAuth>
      <div className="min-h-screen bg-canvas text-ink">
        <aside className="fixed inset-y-0 left-0 z-20 hidden w-[76px] border-r border-line bg-panel md:flex md:flex-col md:items-center">
          <Link href="/" className="mt-5 flex h-10 w-10 items-center justify-center rounded-lg bg-ink text-white" aria-label="Market Analyst">
            <BarChart3 size={19} strokeWidth={2.1} />
          </Link>
          <nav className="mt-8 flex flex-1 flex-col gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={`group flex h-12 w-14 flex-col items-center justify-center gap-1 rounded-lg text-[10px] font-medium transition ${
                    active ? "bg-slate-100 text-ink" : "text-muted hover:bg-slate-50 hover:text-ink"
                  }`}
                  title={item.label}
                >
                  <Icon size={17} strokeWidth={2} />
                  <span className="leading-none">{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>
        <header className="sticky top-0 z-10 border-b border-line bg-panel/90 backdrop-blur md:ml-[76px]">
          <div className="flex h-14 items-center justify-between px-4 md:px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-ink text-white md:hidden">
                <BarChart3 size={18} />
              </div>
              <div>
                <div className="text-sm font-semibold leading-5">Market Analyst</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden text-right sm:block">
                <div className="text-sm font-semibold text-ink">{user ? `${user.firstName} ${user.lastName}`.trim() : "Operator"}</div>
                <div className="text-[11px] text-muted">{user?.email ?? "Signed in"}</div>
              </div>
              <button
                type="button"
                onClick={() => void logout()}
                className="inline-flex h-9 items-center gap-2 rounded-full border border-line bg-white px-3 text-xs font-semibold text-muted transition hover:text-ink"
              >
                <LogOut size={14} />
                Logout
              </button>
            </div>
          </div>
        </header>
        <main className="md:ml-[76px]">{children}</main>
      </div>
    </RequireAuth>
  );
}
