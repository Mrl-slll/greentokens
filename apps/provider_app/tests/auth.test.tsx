import { afterEach, describe, expect, it, vi } from "vitest";
import { createProviderAuth, validServer, type SessionVault, type StoredSession } from "../src/services/providerAuth";
import { credentials, TEST_KEY } from "./fixtures";

afterEach(() => vi.restoreAllMocks());
const response = () => new Response(JSON.stringify({ access_token: TEST_KEY, expires_at: new Date(Date.now() + 86400000).toISOString(),
  account: { displayName: credentials.username, deviceId: credentials.deviceId } }), { status: 201 });

it("signs up at the configured server and keeps credentials out of local storage", async () => {
  const write = vi.spyOn(Storage.prototype, "setItem");
  const fetcher = vi.fn<typeof fetch>().mockResolvedValue(response());
  const auth = createProviderAuth("https://gt.example.com", fetcher);
  await auth.authenticate("signup", credentials);
  expect(fetcher.mock.calls[0][0]).toBe("https://gt.example.com/v1/provider/auth/signup");
  expect(JSON.parse(fetcher.mock.calls[0][1]!.body as string).device_id).toBe(credentials.deviceId);
  expect(fetcher.mock.calls[0][1]).toMatchObject({ credentials: "omit", redirect: "error", cache: "no-store" });
  expect(auth.connection()).toEqual({ server: "https://gt.example.com", key: TEST_KEY, deviceId: credentials.deviceId });
  expect(write).not.toHaveBeenCalled();
});

it("requires login, refuses expired sessions and starts fresh after reopening", async () => {
  const fetcher = vi.fn<typeof fetch>().mockResolvedValue(response());
  const auth = createProviderAuth("https://gt.example.com", fetcher);
  expect(() => auth.connection()).toThrow(/sign in/);
  await auth.authenticate("login", credentials);
  expect(() => createProviderAuth("https://gt.example.com", fetcher).connection()).toThrow(/sign in/);
  vi.spyOn(Date, "now").mockReturnValue(Date.now() + 86400001);
  expect(() => auth.connection()).toThrow(/sign in/);
});

it("revokes a session on sign-out and clears it even if the server is offline", async () => {
  const fetcher = vi.fn<typeof fetch>().mockResolvedValueOnce(response()).mockRejectedValueOnce(new Error("offline"));
  const auth = createProviderAuth("https://gt.example.com", fetcher);
  await auth.authenticate("login", credentials);
  await expect(auth.signOut()).rejects.toThrow(/Signed out on this computer/);
  expect(fetcher.mock.calls[1][0]).toMatch(/auth\/logout$/);
  expect(fetcher.mock.calls[1][1]?.headers).toMatchObject({ Authorization: `Bearer ${TEST_KEY}` });
  expect(() => auth.connection()).toThrow(/sign in/);
});

it("does not display arbitrary server errors or send passwords to an invalid URL", async () => {
  for (const server of ["http://evil.example", "https://user:secret@example.com", "https://example.com/path", "https://example.com/?key=secret"]) {
    expect(validServer(server)).toBe(false);
    const fetcher = vi.fn<typeof fetch>();
    await expect(createProviderAuth(server, fetcher).authenticate("login", credentials)).rejects.toThrow(/server configured/);
    expect(fetcher).not.toHaveBeenCalled();
  }
  const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response("password-must-not-be-shown", { status: 500 }));
  await expect(createProviderAuth("https://gt.example.com", fetcher).authenticate("login", credentials)).rejects.toThrow("GreenTokens could not complete sign-in.");
});

it("explains wrong passwords, duplicate usernames and throttling without saving a session", async () => {
  for (const [status, message] of [[401, /Incorrect/], [409, /unavailable/], [429, /Too many attempts/]] as const) {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status }));
    const auth = createProviderAuth("https://gt.example.com", fetcher);
    await expect(auth.authenticate("login", credentials)).rejects.toThrow(message);
    expect(() => auth.connection()).toThrow(/sign in/);
  }
});

it("Create account never does nothing: problems show a message, and any password is accepted", async () => {
  const { createElement } = await import("react");
  const { cleanup, fireEvent, render, screen } = await import("@testing-library/react");
  const { default: App } = await import("../src/App");
  const { createMockProviderService } = await import("../src/services/mockProviderService");
  localStorage.clear();
  const detect = async () => ({ status: "ok" as const, hardware: { cpuModel: "x", cores: 4, threads: 8, ramGb: 8, gpus: [], os: "Windows", hostname: "PC" } });
  render(createElement(App, { service: createMockProviderService({ delayMs: 0 }), detectHardware: detect }));
  fireEvent.click(screen.getByRole("button", { name: "New here? Create account" }));
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/Username/);
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "rtx-pc-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/Enter a password/);
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "a" } }); // one character: allowed
  fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "a" } });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  expect(await screen.findByText(/Signed in as/)).toBeTruthy();
  cleanup();
});

describe("remembered sign-in (OS secure store)", () => {
  const FRESH = "gt_" + "b".repeat(30);
  const server = "https://gt.example.com";
  function memoryVault(initial: StoredSession | null = null) {
    let stored = initial;
    const vault: SessionVault = {
      load: vi.fn(async () => stored), save: vi.fn(async (s: StoredSession) => { stored = s; }), clear: vi.fn(async () => { stored = null; }),
    };
    return { vault, get: () => stored };
  }
  const remembered = (patch: Partial<StoredSession> = {}): StoredSession => ({ server, token: TEST_KEY,
    expires: Date.now() + 86400000, deviceId: credentials.deviceId, displayName: credentials.username, ...patch });
  const fresh = () => new Response(JSON.stringify({ access_token: FRESH, expires_at: new Date(Date.now() + 30 * 86400000).toISOString(),
    account: { displayName: credentials.username, deviceId: credentials.deviceId } }), { status: 200 });

  it("remembers the session but never the password", async () => {
    const { vault, get } = memoryVault();
    await createProviderAuth(server, vi.fn<typeof fetch>().mockResolvedValue(response()), vault).authenticate("signup", credentials);
    expect(get()).toMatchObject({ server, token: TEST_KEY, deviceId: credentials.deviceId });
    expect(JSON.stringify(get())).not.toContain(credentials.password);
  });

  it("reopening swaps the remembered token for a fresh one, only once per launch", async () => {
    const { vault, get } = memoryVault(remembered());
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(fresh());
    const auth = createProviderAuth(server, fetcher, vault);
    const [a, b] = await Promise.all([auth.restore(), auth.restore()]);
    expect(a).toEqual({ displayName: credentials.username, deviceId: credentials.deviceId });
    expect(b).toEqual(a);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toBe(`${server}/v1/provider/auth/refresh`);
    expect(fetcher.mock.calls[0][1]?.headers).toMatchObject({ Authorization: `Bearer ${TEST_KEY}` });
    expect(auth.connection().key).toBe(FRESH);
    expect(get()?.token).toBe(FRESH);
  });

  it("forgets a revoked, expired or other-server session", async () => {
    for (const [stored, reply] of [[remembered(), new Response("{}", { status: 401 })],
      [remembered({ expires: Date.now() - 1 }), fresh()], [remembered({ server: "https://old.example.com" }), fresh()]] as const) {
      const { vault, get } = memoryVault(stored);
      const auth = createProviderAuth(server, vi.fn<typeof fetch>().mockResolvedValue(reply), vault);
      expect(await auth.restore()).toBeNull();
      expect(get()).toBeNull();
      expect(() => auth.connection()).toThrow(/sign in/);
    }
  });

  it("keeps the remembered session when offline or on a server without refresh", async () => {
    for (const fetcher of [vi.fn<typeof fetch>().mockRejectedValue(new Error("offline")),
      vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 404 }))]) {
      const { vault, get } = memoryVault(remembered());
      const auth = createProviderAuth(server, fetcher, vault);
      expect(await auth.restore()).toEqual({ displayName: credentials.username, deviceId: credentials.deviceId });
      expect(auth.connection().key).toBe(TEST_KEY);
      expect(get()?.token).toBe(TEST_KEY);
    }
  });

  it("a manual sign-in during the background restore wins", async () => {
    const { vault, get } = memoryVault(remembered());
    let release!: (r: Response) => void;
    const slowRefresh = new Promise<Response>((r) => { release = r; });
    const fetcher = vi.fn<typeof fetch>().mockReturnValueOnce(slowRefresh).mockResolvedValueOnce(response());
    const auth = createProviderAuth(server, fetcher, vault);
    const restoring = auth.restore();
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1)); // refresh is in flight
    await auth.authenticate("login", credentials);
    release(fresh());
    expect(await restoring).toBeNull();
    expect(auth.connection().key).toBe(TEST_KEY);
    expect(get()?.token).toBe(TEST_KEY);
  });

  it("sign-out clears the secure store even when the server is unreachable", async () => {
    const { vault, get } = memoryVault(remembered());
    const auth = createProviderAuth(server, vi.fn<typeof fetch>().mockResolvedValueOnce(fresh()).mockRejectedValueOnce(new Error("offline")), vault);
    await auth.restore();
    await expect(auth.signOut()).rejects.toThrow(/Signed out on this computer/);
    expect(get()).toBeNull();
  });
});
