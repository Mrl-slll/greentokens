import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it } from "vitest";
import App from "../src/App";
import { createMockProviderService } from "../src/services/mockProviderService";
import type { HardwareDetector } from "../src/services/hardware";
import type { HardwareResult } from "../src/types/provider";

const laptop: HardwareResult = { status: "ok", hardware: { cpuModel: "Test CPU", cores: 8, threads: 16, ramGb: 16, gpus: [], os: "Windows 11", hostname: "TESTPC" } };
const detect = (r: HardwareResult = laptop): HardwareDetector => async () => r;

beforeEach(() => localStorage.clear());
afterEach(cleanup);

function renderApp(service = createMockProviderService({ delayMs: 0 }), hw = detect()) {
  render(createElement(App, { service, detectHardware: hw }));
  return service;
}

async function signIn() {
  fireEvent.click(screen.getByRole("checkbox", { name: /I understand/ }));
  fireEvent.click(screen.getByRole("button", { name: "Sign in (demo)" }));
  await screen.findByRole("heading", { name: "Your computer" });
}

it("requires explicit consent before sign-in", () => {
  renderApp();
  const button = screen.getByRole("button", { name: "Sign in (demo)" }) as HTMLButtonElement;
  expect(button.disabled).toBe(true);
  fireEvent.click(screen.getByRole("checkbox", { name: /I understand/ }));
  expect(button.disabled).toBe(false);
});

it("shows a friendly error when sign-in fails", async () => {
  const service = createMockProviderService({ delayMs: 0 });
  service.options.failSignIn = true;
  renderApp(service);
  fireEvent.click(screen.getByRole("checkbox", { name: /I understand/ }));
  fireEvent.click(screen.getByRole("button", { name: "Sign in (demo)" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/couldn't sign you in/);
  expect(screen.queryByRole("heading", { name: "Your computer" })).toBeNull();
});

it("starts paused, only shows available after confirmation, and pauses", async () => {
  renderApp();
  await signIn();
  fireEvent.click(screen.getByRole("button", { name: "Continue to computing controls" }));
  expect(screen.getByRole("heading", { name: "Paused" })).toBeTruthy();
  const start = screen.getByRole("button", { name: /Start Computing/ }) as HTMLButtonElement;
  const pause = screen.getByRole("button", { name: /Pause Computing/ }) as HTMLButtonElement;
  expect(pause.disabled).toBe(true);

  fireEvent.click(start);
  expect(screen.getByRole("heading", { name: "Starting…" })).toBeTruthy();
  await screen.findByRole("heading", { name: "Your computer is available for jobs" });

  fireEvent.click(pause);
  await screen.findByRole("heading", { name: "Paused" });
  expect(start.disabled).toBe(false);
});

it("stays paused when GreenTokens is unreachable", async () => {
  const service = renderApp();
  await signIn();
  service.options.disconnected = true;
  fireEvent.click(screen.getByRole("button", { name: "Continue to computing controls" }));
  fireEvent.click(screen.getByRole("button", { name: /Start Computing/ }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/stays paused/);
  expect(screen.getByRole("heading", { name: "Paused" })).toBeTruthy();
});

it("opens paused after a restart while keeping the sign-in and saved limits", async () => {
  renderApp();
  await signIn();
  fireEvent.click(screen.getByRole("button", { name: "Continue to computing controls" }));
  fireEvent.change(screen.getByLabelText(/Processor \(CPU\)/), { target: { value: "70" } });
  fireEvent.click(screen.getByRole("button", { name: "Save preferences" }));
  await screen.findByText(/aren't enforced yet/);
  fireEvent.click(screen.getByRole("button", { name: /Start Computing/ }));
  await screen.findByRole("heading", { name: "Your computer is available for jobs" });

  cleanup(); // "restart" the app
  renderApp();
  fireEvent.click(await screen.findByRole("button", { name: "Computing" }));
  expect(screen.getByRole("heading", { name: "Paused" })).toBeTruthy();
  expect(screen.getByText("Up to 70%")).toBeTruthy();
});

it("shows no-GPU hardware plainly and disables GPU sharing", async () => {
  renderApp();
  await signIn();
  expect(await screen.findByText(/No graphics card detected/)).toBeTruthy();
  expect(screen.getByText("Test CPU")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Continue to computing controls" }));
  expect((screen.getByRole("switch", { name: /Share graphics card/ }) as HTMLButtonElement).disabled).toBe(true);
});

it("shows the browser-preview message when hardware can't be read", async () => {
  renderApp(undefined, detect({ status: "unavailable", reason: "browser", message: "Hardware details are shown in the installed desktop app." }));
  await signIn();
  expect(screen.getByText(/shown in the installed desktop app/)).toBeTruthy();
});

it("never shows invented earnings and lists completed jobs", async () => {
  renderApp();
  await signIn();
  fireEvent.click(screen.getByRole("button", { name: "Activity" }));
  expect(await screen.findByText("Unavailable")).toBeTruthy();
  expect(screen.getByText(/not offered during the pilot/)).toBeTruthy();
  expect(screen.getByText(/No jobs yet/)).toBeTruthy();
});

it("sign out pauses, clears saved state and returns to Welcome", async () => {
  renderApp();
  await signIn();
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
  fireEvent.click(screen.getByRole("button", { name: "Yes, sign out" }));
  await screen.findByRole("button", { name: "Sign in (demo)" });
  expect((screen.getByRole("checkbox", { name: /I understand/ }) as HTMLInputElement).checked).toBe(false);
});
