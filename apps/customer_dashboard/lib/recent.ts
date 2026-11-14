import type { Mode } from "./client";
import type { DevUser } from "./types";
const MAX = 20, key = (m: Mode, u: DevUser) => `gt.recent.${m}.${u}`;
type Store = Pick<Storage, "getItem" | "setItem">;

// Mock jobs live only in memory, so their IDs must too: they vanish on reload, like the mock jobs.
const mem = new Map<string, string>();
const memoryStore: Store = { getItem: (k) => mem.get(k) ?? null, setItem: (k, v) => void mem.set(k, v) };
export const resetMockRecent = () => mem.clear();
/** Live IDs persist in this browser; mock IDs stay in memory. Never mixed (different keys). */
export const storeFor = (m: Mode): Store => (m === "mock" ? memoryStore : localStorage);

export function loadRecent(m: Mode, u: DevUser, s: Store): string[] {
  try { const v = JSON.parse(s.getItem(key(m, u)) ?? "[]"); return Array.isArray(v) ? v.filter((x) => typeof x === "string").slice(0, MAX) : []; } catch { return []; }
}
export function addRecent(m: Mode, u: DevUser, id: string, s: Store): string[] {
  const next = [id, ...loadRecent(m, u, s).filter((x) => x !== id)].slice(0, MAX);
  try { s.setItem(key(m, u), JSON.stringify(next)); } catch { /* storage unavailable: list just won't persist */ }
  return next;
}
