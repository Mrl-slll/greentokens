import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ProviderError, type ProviderService } from "../services/ProviderService";
import type { HardwareDetector } from "../services/hardware";
import { DEFAULT_PREFERENCES, type Account, type Activity, type HardwareResult, type Participation, type Preferences } from "../types/provider";

const STORAGE_KEY = "greentokens.provider.v1";

<<<<<<< HEAD
// Only non-secret device settings are remembered. Account/session are memory-only.
interface Saved { consent: boolean; preferences: Preferences;
  deviceId: string; accountDevices: Record<string, string>; setupDone: boolean; setupNote: string }

const newDeviceId = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `dev-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`);

function load(): Saved {
  const fallback: Saved = { consent: false, preferences: DEFAULT_PREFERENCES,
    deviceId: newDeviceId(), accountDevices: {}, setupDone: false, setupNote: "" };
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    if (!parsed || typeof parsed !== "object") return fallback;
    return { consent: parsed.consent === true,
      preferences: { cpuPercent: parsed.preferences?.cpuPercent ?? DEFAULT_PREFERENCES.cpuPercent,
        ramGb: parsed.preferences?.ramGb ?? DEFAULT_PREFERENCES.ramGb,
        gpuEnabled: parsed.preferences?.gpuEnabled === true, notifications: parsed.preferences?.notifications !== false,
        deviceName: typeof parsed.preferences?.deviceName === "string" ? parsed.preferences.deviceName : "" },
      deviceId: typeof parsed.deviceId === "string" && /^[A-Za-z0-9-]{8,64}$/.test(parsed.deviceId) ? parsed.deviceId : fallback.deviceId,
      accountDevices: Object.fromEntries(Object.entries(parsed.accountDevices ?? {}).filter(([key, value]) =>
        /^account:[a-z0-9][a-z0-9_-]{2,31}$/.test(key) && typeof value === "string" && /^[A-Za-z0-9-]{8,64}$/.test(value)).map(([key, value]) => [key, value as string])),
      setupDone: parsed.setupDone === true, setupNote: typeof parsed.setupNote === "string" ? parsed.setupNote : "" };
=======
// Only consent, account and preferences are remembered. Participation is never
// saved, so the app always opens Paused.
interface Saved { consent: boolean; account: Account | null; preferences: Preferences }

function load(): Saved {
  const fallback: Saved = { consent: false, account: null, preferences: DEFAULT_PREFERENCES };
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    if (!parsed || typeof parsed !== "object") return fallback;
    return { consent: parsed.consent === true, account: parsed.account ?? null,
      preferences: { ...DEFAULT_PREFERENCES, ...(parsed.preferences ?? {}) } };
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
  } catch { return fallback; }
}
function save(s: Saved) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch { /* storage unavailable: keep in memory */ }
}

const friendly = (e: unknown, fallback: string) => (e instanceof ProviderError ? e.message : fallback);

interface ProviderContext {
  service: ProviderService;
  consent: boolean;
  setConsent(v: boolean): void;
  account: Account | null;
<<<<<<< HEAD
  authenticate(mode: "login" | "signup", username: string, password: string): Promise<boolean>;
  signOut(): Promise<void>;
  authError: string | null;
  authenticating: boolean;
  /** Forget this device and consent; pauses first. */
  reset(): Promise<void>;
  participation: Participation;
  controlError: string | null;
  /** consented: pass true when the user has just agreed in the first-connect prompt. */
  start(opts?: { consented?: boolean }): Promise<void>;
=======
  signingIn: boolean;
  signInError: string | null;
  signIn(): Promise<void>;
  signOut(): Promise<void>;
  participation: Participation;
  controlError: string | null;
  start(): Promise<void>;
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
  pause(): Promise<void>;
  preferences: Preferences;
  savePreferences(p: Preferences): Promise<{ enforced: boolean } | null>;
  hardware: HardwareResult | null;
  refreshHardware(): void;
  activity: Activity | null;
<<<<<<< HEAD
  /** True while the one-time setup runs (first Connect, or Repair setup). */
  preparing: boolean;
  setupDone: boolean;
  setupNote: string;
  repairSetup(): Promise<void>;
=======
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
}

const Ctx = createContext<ProviderContext | null>(null);

export function ProviderProvider({ service, detectHardware, children }: { service: ProviderService; detectHardware: HardwareDetector; children: ReactNode }) {
  const [saved, setSaved] = useState<Saved>(load);
<<<<<<< HEAD
  const [account, setAccount] = useState<Account | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authenticating, setAuthenticating] = useState(false);
=======
  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
  const [participation, setParticipationState] = useState<Participation>("paused");
  const participationRef = useRef<Participation>("paused");
  const [controlError, setControlError] = useState<string | null>(null);
  const [hardware, setHardware] = useState<HardwareResult | null>(null);
  const [activity, setActivity] = useState<Activity | null>(null);
<<<<<<< HEAD
  const [preparing, setPreparing] = useState(false);
  // Also remove any credentials saved by older invite-based versions on first load.
  useEffect(() => { save(saved); }, [saved]);
=======
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))

  // Read through a function so TypeScript doesn't keep narrowing across awaits.
  const current = () => participationRef.current;
  const setParticipation = (p: Participation) => { participationRef.current = p; setParticipationState(p); };
  const update = useCallback((patch: Partial<Saved>) => setSaved((s) => { const next = { ...s, ...patch }; save(next); return next; }), []);

  const refreshHardware = useCallback(() => {
    setHardware(null);
    detectHardware().then(setHardware, () => setHardware({ status: "unavailable", reason: "failed", message: "We couldn't read this computer's hardware details." }));
  }, [detectHardware]);
  useEffect(refreshHardware, [refreshHardware]);

<<<<<<< HEAD
  // Poll activity for the lifetime of the app.
  useEffect(() => {
=======
  // Poll activity while signed in.
  const signedIn = saved.account !== null;
  useEffect(() => {
    if (!signedIn) { setActivity(null); return; }
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
    let cancelled = false;
    const tick = () => service.getActivity().then((a) => { if (!cancelled) setActivity(a); }, () => undefined);
    tick();
    const id = setInterval(tick, 1000);
    return () => { cancelled = true; clearInterval(id); };
<<<<<<< HEAD
  }, [service]);
=======
  }, [service, signedIn]);
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))

  const value = useMemo<ProviderContext>(() => ({
    service,
    consent: saved.consent,
    setConsent: (consent) => update({ consent }),
<<<<<<< HEAD
    account,
    authError,
    authenticating,
    async authenticate(mode, username, password) {
      if (current() !== "paused" || preparing || authenticating || account) return false;
      setAuthError(null); setAuthenticating(true);
      try {
        const accountKey = "account:" + username.trim().toLowerCase();
        const deviceId = saved.accountDevices[accountKey] ?? newDeviceId();
        const credentials = { username, password, deviceId };
        setAccount(await (mode === "signup" ? service.signUp(credentials) : service.signIn(credentials)));
        update({ accountDevices: { ...saved.accountDevices, [accountKey]: deviceId } });
        setControlError(null);
        return true;
      } catch (e) { setAuthError(friendly(e, "Could not sign in. Please try again.")); return false; }
      finally { setAuthenticating(false); }
    },
    async signOut() {
      if (preparing || current() === "starting" || current() === "pausing") return;
      const previous = current();
      setParticipation("pausing");
      setAuthError(null);
      try { await service.pause(); }
      catch (e) { setParticipation(previous); setAuthError(friendly(e, "Could not stop sharing. Please disconnect before signing out.")); return; }
      try { await service.signOut(); }
      catch (e) { setAuthError(friendly(e, "Signed out locally. The server session will expire automatically.")); }
      setAccount(null); setControlError(null);
      setParticipation("paused");
    },
    async reset() {
      if (preparing || authenticating || current() === "starting" || current() === "pausing") return;
      const previous = current();
      setParticipation("pausing");
      try { await service.pause(); }
      catch (e) { setParticipation(previous); setControlError(friendly(e, "Could not stop sharing. Try disconnecting again.")); return; }
      setAuthError(null);
      try { await service.signOut(); } catch (e) { setAuthError(friendly(e, "Signed out locally. The server session will expire automatically.")); }
      setAccount(null);
      setParticipation("paused");
      setControlError(null);
      update({ consent: false, preferences: DEFAULT_PREFERENCES, setupDone: false, setupNote: "" });
    },
    participation,
    controlError,
    async start(opts) {
      if (current() !== "paused" || preparing || authenticating || !(saved.consent || opts?.consented)) return;
      if (!account) { setControlError("Sign in below before connecting."); return; }
      setControlError(null); setParticipation("starting");
      try {
        if (!saved.setupDone) {
          // One-time setup after the owner agreed: installs the training packages this computer can use.
          setPreparing(true);
          try { const r = await service.prepare(); update({ setupDone: true, setupNote: r.note }); }
          finally { setPreparing(false); }
        }
        if (current() !== "starting") return; // Disconnect may have been pressed during setup.
        const deviceName = saved.preferences.deviceName || (hardware?.status === "ok" ? hardware.hardware.hostname : "") || "This computer";
        await service.start(saved.preferences, { deviceId: account.deviceId, deviceName,
          cpus: cpusFor(saved.preferences.cpuPercent, hardware) });
        // If the user pressed Pause while we were starting, stay paused.
        if (current() === "starting") setParticipation("active");
        else await service.pause();
=======
    account: saved.account,
    signingIn,
    signInError,
    async signIn() {
      if (!saved.consent) return;
      setSigningIn(true); setSignInError(null);
      try { update({ account: await service.signIn() }); }
      catch (e) { setSignInError(friendly(e, "We couldn't sign you in. Please try again.")); }
      finally { setSigningIn(false); }
    },
    async signOut() {
      setParticipation("paused");
      try { await service.pause(); await service.signOut(); } catch { /* still sign out locally */ }
      setControlError(null);
      update({ account: null, consent: false, preferences: DEFAULT_PREFERENCES });
    },
    participation,
    controlError,
    async start() {
      if (current() !== "paused") return;
      setControlError(null); setParticipation("starting");
      try {
        await service.start(saved.preferences);
        // If the user pressed Pause while we were starting, stay paused.
        if (current() === "starting") setParticipation("active");
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
      } catch (e) {
        if (current() === "starting") setParticipation("paused");
        setControlError(friendly(e, "Computing could not start. Your computer stays paused."));
      }
    },
    async pause() {
      if (current() === "paused" || current() === "pausing") return;
      setControlError(null); setParticipation("pausing");
      try { await service.pause(); setParticipation("paused"); }
      catch (e) {
        // Never claim a pause that wasn't confirmed.
        setParticipation("active");
        setControlError(friendly(e, "Pause could not be confirmed. Please try again."));
      }
    },
    preferences: saved.preferences,
    async savePreferences(preferences) {
      try {
        const result = await service.savePreferences(preferences);
        update({ preferences });
        return result;
      } catch { return null; }
    },
    hardware,
    refreshHardware,
    activity,
<<<<<<< HEAD
    preparing,
    setupDone: saved.setupDone,
    setupNote: saved.setupNote,
    async repairSetup() {
      if (current() !== "paused") return;
      setControlError(null); setPreparing(true);
      try { const r = await service.prepare(); update({ setupDone: true, setupNote: r.note }); }
      catch (e) { setControlError(friendly(e, "Setup didn't finish. Check the internet connection and try again.")); }
      finally { setPreparing(false); }
    },
  }), [service, saved, participation, controlError, hardware, refreshHardware, activity, update, preparing, account, authError, authenticating]);
=======
  }), [service, saved, signingIn, signInError, participation, controlError, hardware, refreshHardware, activity, update]);
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

<<<<<<< HEAD
/** Processor cores to offer: the chosen share of this computer's threads, at least 1. */
export function cpusFor(cpuPercent: number, hardware: HardwareResult | null) {
  const threads = hardware?.status === "ok" ? hardware.hardware.threads : 2;
  return Math.max(1, Math.round((threads * cpuPercent) / 100));
}

=======
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
export function useProvider() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useProvider must be used inside ProviderProvider");
  return ctx;
}
