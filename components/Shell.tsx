"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useApp } from "./AppProvider";
import { DEV_USERS, type DevUser } from "@/lib/types";

const NAV = [["/", "Dashboard"], ["/jobs/new", "New Job"], ["/jobs", "Recent Jobs"], ["/settings", "Settings"]] as const;

export function Shell({ children }: { children: ReactNode }) {
  const path = usePathname(), { user, setUser, mode } = useApp();
  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 md:flex">
      <nav aria-label="Main" className="border-b border-neutral-200 bg-white p-4 md:min-h-screen md:w-56 md:border-b-0 md:border-r">
        <p className="mb-4 text-lg font-semibold text-emerald-700">GreenTokens</p>
        <ul className="flex gap-2 md:flex-col">
          {NAV.map(([href, label]) => {
            const active = href === "/" ? path === "/" : path === href || (href === "/jobs" && path.startsWith("/jobs/") && path !== "/jobs/new");
            return <li key={href}><Link href={href} aria-current={active ? "page" : undefined}
              className={`block rounded px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-emerald-700 ${active ? "bg-emerald-50 font-semibold text-emerald-800" : "hover:bg-neutral-100"}`}>{label}</Link></li>;
          })}
        </ul>
      </nav>
      <div className="flex-1">
        <div role="status" className="bg-amber-100 px-4 py-2 text-sm text-amber-900">Local development — identity stub. Not real authentication.</div>
        <header className="flex flex-wrap items-center justify-end gap-3 border-b border-neutral-200 bg-white px-4 py-2 text-sm">
          <span className={`rounded px-2 py-1 font-semibold ${mode === "mock" ? "bg-purple-100 text-purple-900" : "bg-emerald-100 text-emerald-900"}`}>
            {mode === "mock" ? "MOCK DATA — not real execution" : "LIVE — local backend"}</span>
          <label className="flex items-center gap-2">Development identity
            <select value={user} onChange={(e) => setUser(e.target.value as DevUser)} className="rounded border border-neutral-300 px-2 py-1">
              {DEV_USERS.map((u) => <option key={u}>{u}</option>)}</select></label>
        </header>
        <main className="mx-auto max-w-3xl p-4 md:p-8" key={user /* remount pages on identity change: clears visible data, aborts requests */}>{children}</main>
      </div>
    </div>
  );
}
