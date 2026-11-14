import { describe, expect, it } from "vitest";
import { safeFilename } from "@/lib/download";
import { createMockClient } from "@/lib/mockClient";
import { CPU_ONLY } from "@/lib/types";

describe("safeFilename", () => {
  it("is built only from kind and a UUID-shaped id", () => {
    expect(safeFilename("output", "0b0c0d0e-1111-2222-3333-444455556666")).toBe("greentokens-output-0b0c0d0e-1111-2222-3333-444455556666.json");
    expect(safeFilename("log", "x")).toBe("greentokens-log-.txt".replace("-.", "-unknown."));
    expect(safeFilename("../../etc", "../../passwd")).not.toMatch(/[/\\.]{2}|\//);
  });
});
describe("mock artifacts and usage (MOCK, not live)", () => {
  const sub = (key: string, values = [1, 2, 3, 4]) => ({ template_id: "sum_numbers_v1" as const, requirements: CPU_ONLY, parameters: { values }, idempotency_key: key });
  it("job has output + log artifacts; output text holds the result; log is text/plain", async () => {
    const c = createMockClient(), j = await c.submitJob("alice", sub("a"));
    const d = await c.getJob("alice", j.job_id), out = d.artifacts.find((a) => a.kind === "output")!, log = d.artifacts.find((a) => a.kind === "log")!;
    expect(JSON.parse((await c.getArtifactText("alice", out.artifact_id)).text)).toEqual({ result: 10 });
    expect((await c.getArtifactText("alice", log.artifact_id)).contentType).toBe("text/plain");
  });
  it("another identity cannot fetch the artifact (404)", async () => {
    const c = createMockClient(), j = await c.submitJob("alice", sub("a")), d = await c.getJob("alice", j.job_id);
    await expect(c.getArtifactText("bob", d.artifacts[0].artifact_id)).rejects.toMatchObject({ status: 404 });
  });
  it("uploaded file input gives 10, and usage counts only your org", async () => {
    const c = createMockClient(), up = await c.uploadInput("alice", '{"values":[1,2,3,4]}');
    const j = await c.submitJob("alice", { template_id: "sum_numbers_v1", requirements: CPU_ONLY, input_artifact_id: up.artifact_id, idempotency_key: "f" });
    expect((await c.getResult("alice", j.job_id)).result).toBe(10);
    expect((await c.getUsage("alice")).attempts).toBe(1);
    expect((await c.getUsage("bob")).attempts).toBe(0);
  });
});
