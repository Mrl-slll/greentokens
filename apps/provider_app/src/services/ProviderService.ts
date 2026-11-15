import type { Account, Activity, Preferences } from "../types/provider";

/**
 * Everything the UI needs from GreenTokens. Today only the mock implements it.
 * A live version will talk to the core-owned worker agent (see INTEGRATION.md);
 * screens must not change when it is swapped in.
 */
export interface ProviderService {
  readonly mode: "mock" | "live";
  signIn(): Promise<Account>;
  signOut(): Promise<void>;
  /** Resolves only once the worker/backend confirms the computer is available. */
  start(preferences: Preferences): Promise<void>;
  /** Must stop new work immediately. Resolves once confirmed. */
  pause(): Promise<void>;
  /** Returns whether the limits are actually enforced. */
  savePreferences(preferences: Preferences): Promise<{ enforced: boolean }>;
  getActivity(): Promise<Activity>;
}

/** An error whose message is safe and friendly to show a non-technical user. */
export class ProviderError extends Error {}
