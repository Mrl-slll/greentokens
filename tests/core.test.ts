import { describe, expect, it } from "vitest";
import { parseInline, parseUpload, validateValues } from "@/lib/validation";
import { asDevUser, match } from "@/lib/proxyPolicy";
import { utc } from "@/lib/client";
import { createMockClient } from "@/lib/mockClient";
import { ApiError, CPU_ONLY } from "@/lib/types";

const U = "0b0c0d0e-1111-2222-3333-444455556666";
describe("validation", () => {
  it("accepts 1,2,3,4", () => expect(parseInline("1, 2, 3, 4")).toEqual({ ok: true, values: [1, 2, 3, 4] }));
  it("rejects empty, fractions, text, huge, too many", () => {
    expect(parseInline("").ok).toBe(false);
    expect(parseInline("1.5").ok).toBe(false);
    expect(parseInline("a").ok).toBe(false);
    expect(parseInline("1000000001").ok).toBe(false);
    expect(validateValues(Array(1001).fill(1)).ok).toBe(false);
    expect(validateValues([true]).ok).toBe(false);
  });
  it("upload: valid, bad JSON, extra key, oversize", () => {
    expect(parseUpload('{"values":[1,2,3,4]}')).toEqual({ ok: true, values: [1, 2, 3, 4] });
    expect(parseUpload("{").ok).toBe(false);
    expect(parseUpload('{"values":[1],"x":1}').ok).toBe(false);
    expect(parseUpload(JSON.stringify({ values: [1], pad: "x".repeat(70000) })).ok).toBe(false);
  });
});
describe("proxy allowlist", () => {
  it("allows documented routes", () => {
    expect(match("GET", ["health"])).toBe(0);
    expect(match("POST", ["v1", "jobs"])).toBe(16384);
    expect(match("GET", ["v1", "jobs", U, "result"])).toBe(0);
    expect(match("POST", ["v1", "artifacts"])).toBe(65536);
  });
  it("blocks workers, wrong methods, bad IDs, traversal", () => {
    expect(match("GET", ["v1", "workers"])).toBeNull();
    expect(match("GET", ["v1", "jobs"])).toBeNull();
    expect(match("DELETE", ["v1", "jobs", U])).toBeNull();
    expect(match("GET", ["v1", "jobs", "not-a-uuid"])).toBeNull();
    expect(match("GET", ["v1", "jobs", "..", "workers"])).toBeNull();
  });
  it("only known identities forwarded", () => { expect(asDevUser("alice")).toBe("alice"); expect(asDevUser("mallory")).toBeNull(); });
});
describe("adapter helpers", () => {
  it("treats timezone-less timestamps as UTC", () => {
    expect(utc("2026-11-14T10:00:00")).toBe("2026-11-14T10:00:00Z");
    expect(utc("2026-11-14T10:00:00Z")).toBe("2026-11-14T10:00:00Z");
    expect(utc(null)).toBeNull();
  });
});
describe("mock client (MOCK, not live)", () => {
  const body = { template_id: "sum_numbers_v1" as const, requirements: CPU_ONLY, parameters: { values: [1, 2, 3, 4] }, idempotency_key: "k1" };
  it("sums to 10, replays same key, 409 on changed body, isolates identities", async () => {
    const c = createMockClient();
    const a = await c.submitJob("alice", body);
    expect((await c.submitJob("alice", body)).job_id).toBe(a.job_id);
    await expect(c.submitJob("alice", { ...body, parameters: { values: [9] } })).rejects.toMatchObject({ status: 409 });
    expect((await c.getResult("alice", a.job_id)).result).toBe(10);
    await expect(c.getJob("bob", a.job_id)).rejects.toBeInstanceOf(ApiError);
  });
});
import { addRecent, loadRecent } from "@/lib/recent";
describe("recent ids", () => {
  const mem = () => { const m = new Map<string, string>(); return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) }; };
  it("scopes by identity, dedupes, bounds to 20, survives bad data", () => {
    const s = mem(); addRecent("alice", "a", s); addRecent("alice", "b", s); addRecent("alice", "a", s);
    expect(loadRecent("alice", s)).toEqual(["a", "b"]); expect(loadRecent("bob", s)).toEqual([]);
    for (let i = 0; i < 30; i++) addRecent("bob", `j${i}`, s);
    expect(loadRecent("bob", s)).toHaveLength(20);
    s.setItem("gt.recent.admin", "{not json"); expect(loadRecent("admin", s)).toEqual([]);
  });
});
