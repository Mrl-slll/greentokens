import { afterEach, expect, it, vi } from "vitest";
import { GET, POST } from "@/app/api/core/[...path]/route";
import { CPU_ONLY } from "@/lib/types";

afterEach(() => vi.unstubAllGlobals());
const ctx = (path: string[]) => ({ params: Promise.resolve({ path }) });

it("accepts the largest valid inline input but still rejects oversized requests", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => Response.json({ job_id: "job-1" }, { status: 202 })));
  const body = JSON.stringify({ template_id: "sum_numbers_v1", parameters: { values: Array(1000).fill(-1_000_000_000) }, requirements: CPU_ONLY, idempotency_key: "k".repeat(128) });
  const request = (body: string) => new Request("http://127.0.0.1:3000/api/core/v1/jobs", { method: "POST", body });
  expect((await POST(request(body), ctx(["v1", "jobs"]))).status).toBe(202);
  expect((await POST(request("x".repeat(16_385)), ctx(["v1", "jobs"]))).status).toBe(413);
});

it("blocks foreign origins before contacting the backend", async () => {
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  const response = await POST(new Request("http://127.0.0.1:3000/api/core/v1/jobs", {
    method: "POST", headers: { Origin: "https://unrelated.example" }, body: "{}",
  }), ctx(["v1", "jobs"]));
  expect(response.status).toBe(403); expect(fetch).not.toHaveBeenCalled();
});

it("forwards approved identity and JSON while preserving backend errors", async () => {
  const fetch = vi.fn().mockResolvedValue(Response.json({ detail: "Invalid approved job request" }, { status: 422 }));
  vi.stubGlobal("fetch", fetch);
  const response = await POST(new Request("http://127.0.0.1:3000/api/core/v1/jobs", {
    method: "POST", headers: { Origin: "http://127.0.0.1:3000", "X-Dev-User": "alice" }, body: "{}",
  }), ctx(["v1", "jobs"]));
  expect(response.status).toBe(422);
  expect(fetch).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/jobs", expect.objectContaining({
    headers: { "X-Dev-User": "alice", "Content-Type": "application/json" }, method: "POST",
  }));
});

it("does not expose provider diagnostics", async () => {
  const response = await GET(new Request("http://127.0.0.1:3000/api/core/v1/workers"), ctx(["v1", "workers"]));
  expect(response.status).toBe(404);
});

it("accepts the browser host when Next.js normalizes the internal URL", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ job_id: "job-1" }, { status: 202 })));
  const response = await POST(new Request("http://localhost:3000/api/core/v1/jobs", {
    method: "POST", headers: { Host: "127.0.0.1:3000", Origin: "http://127.0.0.1:3000", "X-Dev-User": "alice" }, body: "{}",
  }), ctx(["v1", "jobs"]));
  expect(response.status).toBe(202);
});
