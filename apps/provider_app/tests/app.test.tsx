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

const connect = () => fireEvent.click(screen.getByRole("button", { name: "Connect" }));
const agree = () => fireEvent.click(screen.getByRole("button", { name: "Agree & Connect" }));

it("opens straight to a single Connect button, disconnected, with no sign-in step", () => {
  renderApp();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Connect" })).toBeTruthy();
  expect(screen.queryByText(/sign in/i)).toBeNull();
});

it("asks for consent on the first Connect and does not connect until the user agrees", async () => {
  renderApp();
  connect();
  expect(screen.getByRole("dialog", { name: "Before you connect" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Not now" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
});

it("connects only after confirmation, then disconnects; later connects don't ask again", async () => {
  renderApp();
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
  service.options.disconnected = true;
  connect();
  agree();
  expect((await screen.findByRole("alert")).textContent).toMatch(/can't reach GreenTokens/);
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
});

it("opens disconnected after a restart while keeping consent and the chosen level", async () => {
  renderApp();
  fireEvent.click(screen.getByRole("radio", { name: /Maximum/ }));
  await screen.findByText(/Limits aren't enforced yet/);
  connect();
  agree();
  await screen.findByRole("heading", { name: "Connected" });

  cleanup(); // "restart" the app
  renderApp();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(screen.getByRole("radio", { name: /Maximum/ }).getAttribute("aria-checked")).toBe("true");
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

it("reset disconnects, forgets consent and asks again next time", async () => {
  renderApp();
  connect();
  agree();
  await screen.findByRole("heading", { name: "Connected" });
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(screen.getByRole("button", { name: "Reset app" }));
  fireEvent.click(screen.getByRole("button", { name: "Yes, reset" }));
  fireEvent.click(screen.getByRole("button", { name: "Home" }));
  expect(await screen.findByRole("heading", { name: "Not connected" })).toBeTruthy();
  connect();
  expect(screen.getByRole("dialog", { name: "Before you connect" })).toBeTruthy();
});
