import type { Account, Credentials } from "../types/provider";
import { ProviderError } from "./ProviderService";

export interface ProviderAuth {
  authenticate(mode: "login" | "signup", credentials: Credentials): Promise<Account>;
  connection(): { server: string; key: string; deviceId: string };
  signOut(): Promise<void>;
}

export function validServer(value: string): boolean {
  try {
    const u = new URL(value);
    return !u.username && !u.password && !u.search && !u.hash && u.pathname === "/" &&
      (u.protocol === "https:" || (u.protocol === "http:" && u.hostname === "127.0.0.1"));
  } catch { return false; }
}

/** Passwords and session tokens stay in memory. Signing in is required after reopening the app. */
export function createProviderAuth(server = __PROVIDER_SERVER__, request: typeof fetch = (...args) => fetch(...args)): ProviderAuth {
  let session: { token: string; expires: number; deviceId: string } | null = null;
  async function post(path: string, body?: Credentials, token?: string) {
    if (!validServer(server)) throw new ProviderError("This app has no valid GreenTokens server configured. Contact the operator for an updated installer.");
    try {
      const response = await request(`${server.replace(/\/$/, "")}/v1/provider/auth/${path}`, {
        method: "POST", credentials: "omit", redirect: "error", cache: "no-store",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: body ? JSON.stringify({ username: body.username.trim().toLowerCase(), password: body.password, device_id: body.deviceId }) : undefined,
        signal: AbortSignal.timeout(20_000),
      });
      if (!response.ok) {
        const messages: Record<number, string> = {
          401: "Incorrect username or password.", 409: "That username is unavailable. Choose another or sign in.",
          422: "Use a 3-32 character username (letters, numbers, underscores or dashes) and enter a password.",
          429: "Too many attempts. Please wait and try again.",
        };
        throw new ProviderError(messages[response.status] ?? "GreenTokens could not complete sign-in. Please try again.");
      }
      return response.status === 204 ? null : await response.json();
    } catch (error) {
      if (error instanceof ProviderError) throw error;
      throw new ProviderError("Can't reach GreenTokens. Check your internet connection; the operator's server must be running.");
    }
  }
  return {
    async authenticate(mode, credentials) {
      const result = await post(mode, credentials);
      const expires = Date.parse(result?.expires_at);
      if (!/^gt_[A-Za-z0-9_-]{20,87}$/.test(result?.access_token ?? "") || !Number.isFinite(expires) || expires <= Date.now() ||
          typeof result?.account?.displayName !== "string" || result?.account?.deviceId !== credentials.deviceId) {
        throw new ProviderError("GreenTokens returned an invalid sign-in response. Please try again.");
      }
      session = { token: result.access_token, expires, deviceId: credentials.deviceId };
      return { displayName: result.account.displayName, deviceId: credentials.deviceId };
    },
    connection() {
      if (!session || session.expires <= Date.now()) {
        session = null;
        throw new ProviderError("Please sign out and sign in again before connecting.");
      }
      return { server: server.replace(/\/$/, ""), key: session.token, deviceId: session.deviceId };
    },
    async signOut() {
      const previous = session;
      session = null;
      if (previous) {
        try { await post("logout", undefined, previous.token); }
        catch { throw new ProviderError("Signed out on this computer. The server could not be reached to revoke the session; it expires automatically within 24 hours."); }
      }
    },
  };
}
