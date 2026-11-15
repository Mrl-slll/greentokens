import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ProviderError, type ProviderService } from "../services/ProviderService";
import type { HardwareDetector } from "../services/hardware";
import { DEFAULT_PREFERENCES, type Account, type Activity, type HardwareResult, type Participation, type Preferences } from "../types/provider";

const STORAGE_KEY = "greentokens.provider.v1";

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
  /** Forget this device and consent; pauses first. */
  reset(): Promise<void>;
  participation: Participation;
  controlError: string | null;
  /** consented: pass true when the user has just agreed in the first-connect prompt. */
  start(opts?: { consented?: boolean }): Promise<void>;
  pause(): Promise<void>;
  preferences: Preferences;
  savePreferences(p: Preferences): Promise<{ enforced: boolean } | null>;
  hardware: HardwareResult | null;
  refreshHardware(): void;
  activity: Activity | null;
}

const Ctx = createContext<ProviderContext | null>(null);

export function ProviderProvider({ service, detectHardware, children }: { service: ProviderService; detectHardware: HardwareDetector; children: ReactNode }) {
  const [saved, setSaved] = useState<Saved>(load);
  const [participation, setParticipationState] = useState<Participation>("paused");
  const participationRef = useRef<Participation>("paused");
  const [controlError, setControlError] = useState<string | null>(null);
  const [hardware, setHardware] = useState<HardwareResult | null>(null);
  const [activity, setActivity] = useState<Activity | null>(null);

  // Read through a function so TypeScript doesn't keep narrowing across awaits.
  const current = () => participationRef.current;
  const setParticipation = (p: Participation) => { participationRef.current = p; setParticipationState(p); };
  const update = useCallback((patch: Partial<Saved>) => setSaved((s) => { const next = { ...s, ...patch }; save(next); return next; }), []);

  const refreshHardware = useCallback(() => {
    setHardware(null);
    detectHardware().then(setHardware, () => setHardware({ status: "unavailable", reason: "failed", message: "We couldn't read this computer's hardware details." }));
  }, [detectHardware]);
  useEffect(refreshHardware, [refreshHardware]);

  // Poll activity for the lifetime of the app.
  useEffect(() => {
    let cancelled = false;
    const tick = () => service.getActivity().then((a) => { if (!cancelled) setActivity(a); }, () => undefined);
    tick();
    const id = setInterval(tick, 1000);
    return () => { cancelled = true; clearInterval(id); };
  }, [service]);

  const value = useMemo<ProviderContext>(() => ({
    service,
    consent: saved.consent,
    setConsent: (consent) => update({ consent }),
    account: saved.account,
    async reset() {
      setParticipation("paused");
      try { await service.pause(); await service.signOut(); } catch { /* still reset locally */ }
      setControlError(null);
      update({ account: null, consent: false, preferences: DEFAULT_PREFERENCES });
    },
    participation,
    controlError,
    async start(opts) {
      if (current() !== "paused" || !(saved.consent || opts?.consented)) return;
      setControlError(null); setParticipation("starting");
      try {
        // First connect registers this device (simulated); there is no separate sign-in step.
        if (!saved.account) update({ account: await service.signIn() });
        await service.start(saved.preferences);
        // If the user pressed Pause while we were starting, stay paused.
        if (current() === "starting") setParticipation("active");
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
  }), [service, saved, participation, controlError, hardware, refreshHardware, activity, update]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useProvider() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useProvider must be used inside ProviderProvider");
  return ctx;
}
