<<<<<<< HEAD
import type { Account, Activity, Credentials, Preferences, PrepareResult } from "../types/provider";

export interface StartContext {
  /** Stable ID for this computer, created once and remembered. */
  deviceId: string;
  /** Name shown to the GreenTokens operator, e.g. the computer name. */
  deviceName: string;
  /** Processor cores this computer offers, already derived from the sharing level. */
  cpus: number;
}

/**
 * Everything the UI needs from GreenTokens. The live version drives the bundled worker, which connects
 * OUTWARD to the GreenTokens server and asks for approved work; the mock is a clearly labelled demo.
 */
export interface ProviderService {
  readonly mode: "mock" | "live";
  signIn(credentials: Credentials): Promise<Account>;
  signUp(credentials: Credentials): Promise<Account>;
  signOut(): Promise<void>;
  /** One-time setup after the owner agrees (installs training packages; minutes the first time). */
  prepare(): Promise<PrepareResult>;
  /** Resolves once the worker is connected to the GreenTokens server. */
  start(preferences: Preferences, context: StartContext): Promise<void>;
  /** Stops taking work. Resolves once confirmed. */
=======
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
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
  pause(): Promise<void>;
  /** Returns whether the limits are actually enforced. */
  savePreferences(preferences: Preferences): Promise<{ enforced: boolean }>;
  getActivity(): Promise<Activity>;
}

/** An error whose message is safe and friendly to show a non-technical user. */
export class ProviderError extends Error {}
