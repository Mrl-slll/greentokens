import { DEV_USERS, type DevUser } from "./types";
const UUID = "[0-9a-f-]{36}";
const RULES: { method: string; re: RegExp; maxBody: number }[] = [
  { method: "GET", re: /^health$/, maxBody: 0 },
  { method: "POST", re: /^v1\/jobs$/, maxBody: 8192 },
  { method: "GET", re: new RegExp(`^v1/jobs/${UUID}$`), maxBody: 0 },
  { method: "GET", re: new RegExp(`^v1/jobs/${UUID}/result$`), maxBody: 0 },
  { method: "POST", re: new RegExp(`^v1/jobs/${UUID}/cancel$`), maxBody: 0 },
  { method: "POST", re: /^v1\/artifacts$/, maxBody: 65_536 },
  { method: "GET", re: new RegExp(`^v1/artifacts/${UUID}$`), maxBody: 0 },
  { method: "GET", re: /^v1\/usage$/, maxBody: 0 },
];
export const UPSTREAM = "http://127.0.0.1:8000"; // fixed; never taken from the request

/** Returns the body limit if the method+path is allowlisted, else null. /v1/workers is deliberately absent. */
export function match(method: string, segments: string[]): number | null {
  if (segments.some((s) => s === "" || s === "." || s === ".." || s.includes("%") || s.includes("\\"))) return null;
  const path = segments.join("/");
  return RULES.find((r) => r.method === method && r.re.test(path))?.maxBody ?? null;
}
export const asDevUser = (v: string | null): DevUser | null => (DEV_USERS as readonly string[]).includes(v ?? "") ? (v as DevUser) : null;
