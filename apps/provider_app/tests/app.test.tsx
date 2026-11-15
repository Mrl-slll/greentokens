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
  await screen.findByRole("button", { name: "Connect", hidden: false });
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
  expect(screen.queryByRole("radiogroup")).toBeNull();
});

it("starts disconnected, only shows Connected after confirmation, and disconnects", async () => {
  renderApp();
  await signIn();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));
  expect(screen.getByRole("heading", { name: "Connecting…" })).toBeTruthy();
  await screen.findByRole("heading", { name: "Connected" });
  fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
  await screen.findByRole("heading", { name: "Not connected" });
});

it("stays disconnected when GreenTokens is unreachable", async () => {
  const service = renderApp();
  await signIn();
  service.options.disconnected = true;
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/stays paused/);
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
});

it("opens disconnected after a restart while keeping the sign-in and chosen level", async () => {
  renderApp();
  await signIn();
  fireEvent.click(screen.getByRole("radio", { name: /Maximum/ }));
  await screen.findByText(/Limits aren't enforced yet/);
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));
  await screen.findByRole("heading", { name: "Connected" });

  cleanup(); // "restart" the app
  renderApp();
  await screen.findByRole("button", { name: "Connect" });
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(screen.getByRole("radio", { name: /Maximum/ }).getAttribute("aria-checked")).toBe("true");
});

it("shows no-GPU hardware plainly", async () => {
  renderApp();
  await signIn();
  fireEvent.click(screen.getByRole("button", { name: "My computer" }));
  expect(await screen.findByText(/No graphics card detected/)).toBeTruthy();
  expect(screen.getByText("Test CPU")).toBeTruthy();
});

it("shows the browser-preview message when hardware can't be read", async () => {
  renderApp(undefined, detect({ status: "unavailable", reason: "browser", message: "Hardware details are shown in the installed desktop app." }));
  await signIn();
  fireEvent.click(screen.getByRole("button", { name: "My computer" }));
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
