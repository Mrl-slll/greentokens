import type { DevUser } from "./types";
const MAX = 20, key = (u: DevUser) => `gt.recent.${u}`;
type Store = Pick<Storage, "getItem" | "setItem">;
export function loadRecent(u: DevUser, s: Store): string[] {
  try { const v = JSON.parse(s.getItem(key(u)) ?? "[]"); return Array.isArray(v) ? v.filter((x) => typeof x === "string").slice(0, MAX) : []; } catch { return []; }
}
export function addRecent(u: DevUser, id: string, s: Store): string[] {
  const next = [id, ...loadRecent(u, s).filter((x) => x !== id)].slice(0, MAX);
  try { s.setItem(key(u), JSON.stringify(next)); } catch { /* storage unavailable: list just won't persist */ }
  return next;
}
