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
async function startGroup() {
  fireEvent.click(screen.getByRole("button", { name: "Start a group" }));
  await screen.findByText(/This computer leads the group/);
}
const agree = () => fireEvent.click(screen.getByRole("button", { name: "Agree & Connect" }));

it("opens straight to a single Connect button, disconnected, with no sign-in step", () => {
  renderApp();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Connect" })).toBeTruthy();
  expect(screen.queryByText(/sign in/i)).toBeNull();
});

it("asks for consent on the first Connect and does not connect until the user agrees", async () => {
  renderApp();
  await startGroup();
  connect();
  expect(screen.getByRole("dialog", { name: "Before you connect" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Not now" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
});

it("connects only after confirmation, then disconnects; later connects don't ask again", async () => {
  renderApp();
  await startGroup();
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
  await startGroup();
  service.options.disconnected = true;
  connect();
  agree();
  expect((await screen.findByRole("alert")).textContent).toMatch(/can't reach GreenTokens/);
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
});

it("opens disconnected after a restart while keeping consent and the chosen level", async () => {
  renderApp();
  await startGroup();
  fireEvent.click(screen.getByRole("radio", { name: /Maximum/ }));
  await screen.findByText(/Limits aren't enforced yet/);
  connect();
  agree();
  await screen.findByRole("heading", { name: "Connected" });

  cleanup(); // "restart" the app
  renderApp();
  expect(screen.getByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(await screen.findByRole("radio", { name: /Maximum/, checked: true })).toBeTruthy(); // after hardware loads
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

it("reset disconnects, forgets the group and consent, and asks again next time", async () => {
  renderApp();
  await startGroup();
  connect();
  agree();
  await screen.findByRole("heading", { name: "Connected" });
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(screen.getByRole("button", { name: "Reset app" }));
  fireEvent.click(screen.getByRole("button", { name: "Yes, reset" }));
  fireEvent.click(screen.getByRole("button", { name: "Home" }));
  expect(await screen.findByRole("heading", { name: "Not connected" })).toBeTruthy();
  expect(screen.getByText(/Start or join a group below first/)).toBeTruthy(); // group forgotten
  await startGroup();
  connect();
  expect(screen.getByRole("dialog", { name: "Before you connect" })).toBeTruthy(); // consent asked again
});

it("won't connect before a group is set up", () => {
  renderApp();
  expect((screen.getByRole("button", { name: "Connect" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText(/Start or join a group below first/)).toBeTruthy();
});

it("rejects a malformed join code and accepts a valid one", async () => {
  renderApp();
  fireEvent.click(screen.getByRole("button", { name: "Join a group" }));
  fireEvent.change(screen.getByLabelText(/Group code/), { target: { value: "not-a-code" } });
  fireEvent.click(screen.getByRole("button", { name: "Join" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/doesn't look right/);
  fireEvent.change(screen.getByLabelText(/Group code/), { target: { value: " GT1-192.168.1.20-0123456789abcdef0123456789abcdef " } });
  fireEvent.click(screen.getByRole("button", { name: "Join" }));
  expect(await screen.findByText(/Joined the group led by/)).toBeTruthy();
  expect(screen.getByText("192.168.1.20")).toBeTruthy();
});

it("leader sees a shareable code", async () => {
  renderApp();
  await startGroup();
  expect(screen.getByText(/^GT1-192\.168\.1\.10-[0-9a-f]{32}$/)).toBeTruthy();
});
