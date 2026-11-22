import type { Account, Credentials } from "../types/provider";
import { ProviderError } from "./ProviderService";

export interface ProviderAuth {
  authenticate(mode: "login" | "signup", credentials: Credentials): Promise<Account>;
  /** Signs in again with the session remembered by the OS secure store, if any. */
  restore(): Promise<Account | null>;
  connection(): { server: string; key: string; deviceId: string };
  signOut(): Promise<void>;
}

/** What is remembered between launches. Never the password. */
export interface StoredSession { server: string; token: string; expires: number; deviceId: string; displayName: string }

/** OS secure store (Windows Credential Manager / macOS Keychain) behind Tauri commands. */
export interface SessionVault {
  load(): Promise<StoredSession | null>;
  save(session: StoredSession): Promise<void>;
  clear(): Promise<void>;
}

const TOKEN = /^gt_[A-Za-z0-9_-]{20,87}$/;
const DEVICE = /^[A-Za-z0-9-]{8,64}$/;

function parseStored(raw: unknown): StoredSession | null {
  try {
    const s = typeof raw === "string" ? JSON.parse(raw) : null;
    if (s && typeof s.server === "string" && TOKEN.test(s.token ?? "") && Number.isFinite(s.expires) &&
        DEVICE.test(s.deviceId ?? "") && typeof s.displayName === "string") {
      return { server: s.server, token: s.token, expires: s.expires, deviceId: s.deviceId, displayName: s.displayName };
    }
  } catch { /* malformed: treat as signed out */ }
  return null;
}

/** Uses the native secure store inside the installed app; remembers nothing in a plain browser. */
export function nativeVault(): SessionVault {
  const inApp = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
  if (!inApp) return { load: async () => null, save: async () => undefined, clear: async () => undefined };
  const call = async <T>(command: string, args?: Record<string, unknown>) =>
    (await import("@tauri-apps/api/core")).invoke<T>(command, args);
  return {
    load: async () => parseStored(await call<string | null>("session_load")),
    save: (session) => call<void>("session_save", { session: JSON.stringify(session) }),
    clear: () => call<void>("session_clear"),
  };
}

export function validServer(value: string): boolean {
  try {
    const u = new URL(value);
    return !u.username && !u.password && !u.search && !u.hash && u.pathname === "/" &&
      (u.protocol === "https:" || (u.protocol === "http:" && u.hostname === "127.0.0.1"));
  } catch { return false; }
}

class HttpStatus extends ProviderError { constructor(message: string, readonly status: number) { super(message); } }

/** Passwords never leave memory. The session token is kept only in the OS secure store. */
export function createProviderAuth(server = __PROVIDER_SERVER__, request: typeof fetch = (...args) => fetch(...args),
  vault: SessionVault = nativeVault()): ProviderAuth {
  const origin = server.replace(/\/$/, "");
  let session: StoredSession | null = null;

  async function post(path: string, body?: Record<string, string>, token?: string) {
    if (!validServer(server)) throw new ProviderError("This app has no valid GreenTokens server configured. Contact the operator for an updated installer.");
    let response: Response;
    try {
      response = await request(`${origin}/v1/provider/auth/${path}`, {
        method: "POST", credentials: "omit", redirect: "error", cache: "no-store",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: body ? JSON.stringify(body) : undefined,
        signal: AbortSignal.timeout(20_000),
      });
    } catch {
      throw new ProviderError("Can't reach GreenTokens. Check your internet connection; the operator's server must be running.");
    }
    if (!response.ok) {
      const messages: Record<number, string> = {
        401: "Incorrect username or password.", 409: "That username is unavailable. Choose another or sign in.",
        422: "Use a 3-32 character username (letters, numbers, underscores or dashes) and enter a password.",
        429: "Too many attempts. Please wait and try again.",
      };
      throw new HttpStatus(messages[response.status] ?? "GreenTokens could not complete sign-in. Please try again.", response.status);
    }
    try { return response.status === 204 ? null : await response.json(); }
    catch { throw new ProviderError("GreenTokens returned an invalid sign-in response. Please try again."); }
  }

  /** Validates a sign-in reply and makes it the current session (remembered securely). */
  async function accept(result: any, deviceId: string): Promise<Account> {
    const expires = Date.parse(result?.expires_at);
    if (!TOKEN.test(result?.access_token ?? "") || !Number.isFinite(expires) || expires <= Date.now() ||
        typeof result?.account?.displayName !== "string" || result?.account?.deviceId !== deviceId) {
      throw new ProviderError("GreenTokens returned an invalid sign-in response. Please try again.");
    }
    manual = true;
    session = { server: origin, token: result.access_token, expires, deviceId, displayName: result.account.displayName };
    try { await vault.save(session); } catch { /* still signed in for this launch */ }
    return { displayName: session.displayName, deviceId };
  }

  let restoring: Promise<Account | null> | null = null;
  /** Set once any sign-in reply is accepted, so a slower background restore never replaces it. */
  let manual = false;

  async function forget() {
    session = null;
    try { await vault.clear(); } catch { /* nothing more we can do locally */ }
  }

  async function restoreOnce(): Promise<Account | null> {
    let stored: StoredSession | null = null;
    try { stored = await vault.load(); } catch { return null; }
    if (!stored) return null;
    if (stored.server !== origin || stored.expires <= Date.now()) { await forget(); return null; }
    let reply: unknown;
    try {
      // Swap for a fresh session: the remembered token stops working once it is used.
      reply = await post("refresh", { device_id: stored.deviceId }, stored.token);
    } catch (e) {
      // Offline, server busy, or an older server without /refresh: keep the remembered session until it expires.
      const keep = !(e instanceof HttpStatus) || [404, 405, 429].includes(e.status) || e.status >= 500;
      if (manual) return null;
      if (!keep) { await forget(); return null; }
      session = stored;
      return { displayName: stored.displayName, deviceId: stored.deviceId };
    }
    if (manual) return null; // the owner signed in by hand meanwhile
    try { return await accept(reply, stored.deviceId); }
    catch { await forget(); return null; }
  }

  return {
    async authenticate(mode, credentials) {
      const result = await post(mode, { username: credentials.username.trim().toLowerCase(),
        password: credentials.password, device_id: credentials.deviceId });
      return accept(result, credentials.deviceId);
    },
    restore() {
      // Once per launch: a remembered token can only be swapped once.
      restoring ??= restoreOnce();
      return restoring;
    },
    connection() {
      if (!session || session.expires <= Date.now()) {
        session = null;
        throw new ProviderError("Please sign out and sign in again before connecting.");
      }
      return { server: origin, key: session.token, deviceId: session.deviceId };
    },
    async signOut() {
      const previous = session;
      await forget();
      if (previous) {
        try { await post("logout", undefined, previous.token); }
        catch { throw new ProviderError("Signed out on this computer. The server could not be reached to revoke the session; it expires automatically."); }
      }
    },
  };
}
