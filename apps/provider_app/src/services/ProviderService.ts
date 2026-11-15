import type { Account, Activity, Group, Preferences, PrepareResult } from "../types/provider";

export interface StartContext {
  group: Group | null;
  /** Processor cores this computer offers, already derived from the sharing level. */
  cpus: number;
}

/**
 * Everything the UI needs from GreenTokens. Today only the mock implements it.
 * A live version will talk to the core-owned worker agent (see INTEGRATION.md);
 * screens must not change when it is swapped in.
 */
export interface ProviderService {
  readonly mode: "mock" | "live";
  signIn(): Promise<Account>;
  signOut(): Promise<void>;
  /** One-time setup (may take minutes the first time) plus a network check. */
  prepare(): Promise<PrepareResult>;
  /** Resolves only once the computer has actually joined (or started) its group. */
  start(preferences: Preferences, context: StartContext): Promise<void>;
  /** Must stop new work immediately. Resolves once confirmed. */
  pause(): Promise<void>;
  /** Returns whether the limits are actually enforced. */
  savePreferences(preferences: Preferences): Promise<{ enforced: boolean }>;
  getActivity(): Promise<Activity>;
}

/** An error whose message is safe and friendly to show a non-technical user. */
export class ProviderError extends Error {}
