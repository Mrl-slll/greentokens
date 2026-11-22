// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import JobPage from "@/app/jobs/[id]/page";

const client = vi.hoisted(() => ({ getJob: vi.fn(), getResult: vi.fn(), getArtifactText: vi.fn() }));
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "training-job" }) }));
vi.mock("@/components/AppProvider", () => ({ useApp: () => ({ client, user: "alice", mode: "live" }) }));
afterEach(cleanup);

it("renders an actual model result, offers download, and retrieves approved logs", async () => {
  client.getJob.mockResolvedValue({ job_id: "training-job", template_id: "linear_regression_v1", status: "SUCCEEDED", input_source: "inline", created_at: "2026-11-14T12:00:00Z", attempt_count: 1,
    artifacts: [{ artifact_id: "log-1", kind: "log", size_bytes: 20, sha256: "abc", expires_at: "2026-11-15T12:00:00Z" }] });
  client.getResult.mockResolvedValue({ result: { model_type: "linear_regression", slope: 2, intercept: 1, training_mse: 0, samples: 5 }, job_id: "training-job", attempt_id: "attempt" });
  client.getArtifactText.mockResolvedValue({ text: "Approved pipeline completed", contentType: "text/plain" });
  render(createElement(JobPage));
  expect(await screen.findByText(/Trained model: y = 2/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Download result JSON" }).getAttribute("download")).toBe("greentokens-training-job.json");
  fireEvent.click(screen.getByRole("button", { name: "View log" }));
  expect(await screen.findByText("Approved pipeline completed")).toBeTruthy();
  expect(client.getArtifactText).toHaveBeenCalledWith("alice", "log-1");
});
