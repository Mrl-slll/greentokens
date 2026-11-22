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
  /** Sign-in remembered securely from an earlier launch, if still valid. */
  restore(): Promise<Account | null>;
  /** One-time setup after the owner agrees (installs training packages; minutes the first time). */
  prepare(): Promise<PrepareResult>;
  /** Resolves once the worker is connected to the GreenTokens server. */
  start(preferences: Preferences, context: StartContext): Promise<void>;
  /** Stops taking work. Resolves once confirmed. */
  pause(): Promise<void>;
  /** Returns whether the limits are actually enforced. */
  savePreferences(preferences: Preferences): Promise<{ enforced: boolean }>;
  getActivity(): Promise<Activity>;
}

/** An error whose message is safe and friendly to show a non-technical user. */
export class ProviderError extends Error {}
