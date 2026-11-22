import { createElement } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";
import { createMockProviderService } from "../src/services/mockProviderService";
import type { HardwareDetector } from "../src/services/hardware";
import type { HardwareResult } from "../src/types/provider";

const laptop: HardwareResult = { status: "ok", hardware: { cpuModel: "Test CPU", cores: 8, threads: 16, ramGb: 16, gpus: [], os: "Windows 11", hostname: "TESTPC" } };
const detect = (r: HardwareResult = laptop): HardwareDetector => async () => r;
import { signIn } from "./fixtures";

beforeEach(() => localStorage.clear());
afterEach(cleanup);

function renderApp(service = createMockProviderService({ delayMs: 0 }), hw = detect()) {
  render(createElement(App, { service, detectHardware: hw }));
  return service;
}

const connect = () => fireEvent.click(screen.getByRole("button", { name: "Connect" }));
const agree = () => fireEvent.click(screen.getByRole("button", { name: "Yes, set up & connect" }));

it("opens straight to a single Connect button, disconnected", () => {
  renderApp();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Connect" })).toBeTruthy();
});

it("asks once to set up the computer and does not connect until the owner agrees", async () => {
  renderApp();
  await signIn();
  connect();
  const dialog = screen.getByRole("dialog", { name: "Before you connect" });
  expect(dialog.textContent).toMatch(/Allow GreenTokens to set up this computer/);
  expect(dialog.textContent).toMatch(/PyTorch/);
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Not now" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
});

it("sets up and connects only after Yes, then disconnects; later connects don't ask again", async () => {
  renderApp();
  await signIn();
  connect();
  agree();
  expect(screen.getByRole("heading", { name: "Connecting…" })).toBeTruthy();
  await screen.findByRole("heading", { name: "Connected" });
  fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
  await screen.findByRole("heading", { name: "Not connected" });
  connect();
  expect(screen.queryByRole("dialog")).toBeNull();
  await screen.findByRole("heading", { name: "Connected" });
});

it("stays disconnected and explains when GreenTokens is unreachable", async () => {
  const service = renderApp();
  await signIn();
  service.options.disconnected = true;
  connect();
  agree();
  expect((await screen.findByRole("alert")).textContent).toMatch(/can't reach GreenTokens/);
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
});

it("opens disconnected after a restart while keeping consent and preferences but requiring sign-in", async () => {
  renderApp();
  await signIn();
  fireEvent.click(screen.getByRole("radio", { name: /Maximum/ }));
  await screen.findByText(/Limits aren't enforced yet/);
  connect();
  agree();
  await screen.findByRole("heading", { name: "Connected" });

  cleanup(); // "restart" the app
  renderApp();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(await screen.findByRole("radio", { name: /Maximum/, checked: true })).toBeTruthy(); // after hardware loads
  expect(screen.getByLabelText("Username")).toBeTruthy();
  await signIn();
  connect();
  expect(screen.queryByRole("dialog")).toBeNull(); // already agreed
});

it("shows no-GPU hardware plainly", async () => {
  renderApp();
  fireEvent.click(screen.getByRole("button", { name: "My computer" }));
  expect(await screen.findByText(/No graphics card detected/)).toBeTruthy();
  expect(screen.getByText("Test CPU")).toBeTruthy();
});

it("shows the browser-preview message when hardware can't be read", async () => {
  renderApp(undefined, detect({ status: "unavailable", reason: "browser", message: "Hardware details are shown in the installed desktop app." }));
  fireEvent.click(screen.getByRole("button", { name: "My computer" }));
  expect(await screen.findByText(/shown in the installed desktop app/)).toBeTruthy();
});

it("never shows invented earnings", async () => {
  renderApp();
  fireEvent.click(screen.getByRole("button", { name: "Activity" }));
  expect(await screen.findByText("Unavailable")).toBeTruthy();
  expect(screen.getByText(/not offered during the pilot/)).toBeTruthy();
  expect(screen.getByText(/No jobs yet/)).toBeTruthy();
});

it("reset disconnects, signs out and clears consent, and asks again next time", async () => {
  renderApp();
  await signIn();
  connect();
  agree();
  await screen.findByRole("heading", { name: "Connected" });
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(screen.getByRole("button", { name: "Reset app" }));
  fireEvent.click(screen.getByRole("button", { name: "Yes, reset" }));
  fireEvent.click(screen.getByRole("button", { name: "Home" }));
  expect(await screen.findByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(await screen.findByText(/Sign in below before connecting/)).toBeTruthy(); // invite forgotten
  await signIn();
  connect();
  expect(screen.getByRole("dialog", { name: "Before you connect" })).toBeTruthy(); // consent asked again
});

it("will not connect before sign-in", () => {
  renderApp();
  expect((screen.getByRole("button", { name: "Connect" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.queryByLabelText("Invite code")).toBeNull();
});

it("creates an account only when passwords match", async () => {
  renderApp();
  fireEvent.click(screen.getByRole("button", { name: "New here? Create account" }));
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "provider-one" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "test-only-password-123" } });
  fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "different-password-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/Passwords do not match/);
  fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "test-only-password-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  await screen.findByText("Signed in as provider-one");
  expect(localStorage.getItem("greentokens.provider.v1")).not.toContain("test-only-password-123");
});

it("shows a failed login and keeps sharing disabled", async () => {
  const service = renderApp();
  service.options.failSignIn = true;
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "provider-one" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "test-only-password-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/Incorrect username or password/);
  expect((screen.getByRole("button", { name: "Connect" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByLabelText("Password") as HTMLInputElement).value).toBe("");
});

it("sign-out disconnects and leaves preferences intact", async () => {
  renderApp();
  await signIn(); connect(); agree();
  await screen.findByRole("heading", { name: "Connected" });
  fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
  await screen.findByRole("button", { name: "Sign in" });
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(JSON.parse(localStorage.getItem("greentokens.provider.v1")!).consent).toBe(true);
});

it("removes old saved invites and placeholder accounts without reusing credentials", async () => {
  localStorage.setItem("greentokens.provider.v1", JSON.stringify({ account: { displayName: "old" },
    invite: { server: "https://old.example", key: "old-private-credential" }, consent: true }));
  renderApp();
  expect(await screen.findByLabelText("Username")).toBeTruthy();
  expect(localStorage.getItem("greentokens.provider.v1")).not.toContain("old-private-credential");
  expect(JSON.parse(localStorage.getItem("greentokens.provider.v1")!)).not.toHaveProperty("account");
});

it("keeps a separate stable device identity for each account on this computer", async () => {
  renderApp();
  await signIn();
  const initial = JSON.parse(localStorage.getItem("greentokens.provider.v1")!).accountDevices["account:provider-one"];
  fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
  await screen.findByRole("button", { name: "Sign in" });
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "provider-two" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "test-only-password-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByText("Signed in as provider-two");
  const devices = JSON.parse(localStorage.getItem("greentokens.provider.v1")!).accountDevices;
  expect(devices["account:provider-two"]).not.toBe(initial);
  fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
  await screen.findByRole("button", { name: "Sign in" });
  await signIn();
  expect(JSON.parse(localStorage.getItem("greentokens.provider.v1")!).accountDevices["account:provider-one"]).toBe(initial);
});

it("does not start the worker if the owner disconnects while setup is running", async () => {
  const service = createMockProviderService({ delayMs: 0 });
  let finish!: () => void;
  vi.spyOn(service, "prepare").mockImplementation(() => new Promise((resolve) => {
    finish = () => resolve({ torch: null, gpu: null, gpuReady: false, note: "done" });
  }));
  const start = vi.spyOn(service, "start");
  renderApp(service);
  await signIn(); connect(); agree();
  fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
  await screen.findByRole("heading", { name: "Not connected" });
  await act(async () => finish());
  expect(start).not.toHaveBeenCalled();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
});
