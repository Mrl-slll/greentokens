// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import NewJob from "@/app/jobs/new/page";

const state = vi.hoisted(() => ({ submitJob: vi.fn(), uploadInput: vi.fn(), push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: state.push }) }));
vi.mock("@/components/AppProvider", () => ({ useApp: () => ({
  client: state, user: "alice", mode: "live",
}) }));
beforeEach(() => { vi.resetAllMocks(); localStorage.clear(); });
afterEach(cleanup);

it("retries ambiguous inline submissions with the same key, but gives changed input a new key", async () => {
  state.submitJob.mockRejectedValue(new Error("Connection lost"));
  render(createElement(NewJob));
  const submit = () => fireEvent.click(screen.getByRole("button", { name: "Submit job" }));
  submit();
  await screen.findByRole("alert");
  const first = state.submitJob.mock.calls[0][1];
  submit();
  await waitFor(() => expect(state.submitJob).toHaveBeenCalledTimes(2));
  expect(state.submitJob.mock.calls[1][1]).toEqual(first);
  await screen.findByRole("button", { name: "Submit job" });
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "5,6" } });
  submit();
  await waitFor(() => expect(state.submitJob).toHaveBeenCalledTimes(3));
  expect(state.submitJob.mock.calls[2][1].idempotency_key).not.toBe(first.idempotency_key);
});

it("reuses the uploaded artifact and submission key after an uncertain response", async () => {
  state.uploadInput.mockResolvedValue({ artifact_id: "input-123" });
  state.submitJob.mockRejectedValueOnce(new Error("Connection lost")).mockResolvedValueOnce({ job_id: "job-123" });
  render(createElement(NewJob));
  const file = new File(['{"values":[1,2,3,4]}'], "input.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => '{"values":[1,2,3,4]}' });
  fireEvent.change(screen.getByLabelText(/Or upload/), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload and submit" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Upload and submit" }));
  await waitFor(() => expect(state.push).toHaveBeenCalledWith("/jobs/job-123"));
  expect(state.uploadInput).toHaveBeenCalledTimes(1);
  expect(state.submitJob.mock.calls[1][1]).toEqual(state.submitJob.mock.calls[0][1]);
});
