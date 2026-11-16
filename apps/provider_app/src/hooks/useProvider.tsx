import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ProviderError, type ProviderService } from "../services/ProviderService";
import type { HardwareDetector } from "../services/hardware";
import { newGroupToken } from "../services/liveProviderService";
import { DEFAULT_PREFERENCES, GROUP_CODE_RE, type Account, type Activity, type Group, type HardwareResult, type Participation, type Preferences } from "../types/provider";

const STORAGE_KEY = "greentokens.provider.v1";

// Only consent, account, preferences and the group are remembered. Participation is never
// saved, so the app always opens disconnected.
interface Saved { consent: boolean; account: Account | null; preferences: Preferences; group: Group | null }

function load(): Saved {
  const fallback: Saved = { consent: false, account: null, preferences: DEFAULT_PREFERENCES, group: null };
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    if (!parsed || typeof parsed !== "object") return fallback;
    return { consent: parsed.consent === true, account: parsed.account ?? null,
      preferences: { ...DEFAULT_PREFERENCES, ...(parsed.preferences ?? {}) },
      group: parsed.group && (parsed.group.role === "host" || parsed.group.role === "member") && GROUP_CODE_RE.test(parsed.group.code) ? parsed.group : null };
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
  group: Group | null;
  /** True while the one-time setup / network check runs. */
  preparing: boolean;
  groupError: string | null;
  createGroup(): Promise<void>;
  joinGroup(code: string): Promise<boolean>;
  leaveGroup(): Promise<void>;
}

const Ctx = createContext<ProviderContext | null>(null);

export function ProviderProvider({ service, detectHardware, children }: { service: ProviderService; detectHardware: HardwareDetector; children: ReactNode }) {
  const [saved, setSaved] = useState<Saved>(load);
  const [participation, setParticipationState] = useState<Participation>("paused");
  const participationRef = useRef<Participation>("paused");
  const [controlError, setControlError] = useState<string | null>(null);
  const [hardware, setHardware] = useState<HardwareResult | null>(null);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [groupError, setGroupError] = useState<string | null>(null);

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
      setGroupError(null);
      update({ account: null, consent: false, preferences: DEFAULT_PREFERENCES, group: null });
    },
    participation,
    controlError,
    async start(opts) {
      if (current() !== "paused" || !(saved.consent || opts?.consented)) return;
      setControlError(null); setParticipation("starting");
      try {
        // First connect registers this device (simulated); there is no separate sign-in step.
        if (!saved.account) update({ account: await service.signIn() });
        await service.start(saved.preferences, { group: saved.group, cpus: cpusFor(saved.preferences.cpuPercent, hardware) });
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
    group: saved.group,
    preparing,
    groupError,
    async createGroup() {
      setGroupError(null); setPreparing(true);
      try {
        const { lanIp } = await service.prepare();
        update({ group: { role: "host", code: `GT1-${lanIp}-${newGroupToken()}` } });
      } catch (e) { setGroupError(friendly(e, "Couldn't set up a group on this computer. Please try again.")); }
      finally { setPreparing(false); }
    },
    async joinGroup(code) {
      const clean = code.trim();
      setGroupError(null);
      if (!GROUP_CODE_RE.test(clean)) { setGroupError("That group code doesn't look right. Copy it again from the leader's computer."); return false; }
      setPreparing(true);
      try { await service.prepare(); update({ group: { role: "member", code: clean } }); return true; }
      catch (e) { setGroupError(friendly(e, "Couldn't prepare this computer. Please try again.")); return false; }
      finally { setPreparing(false); }
    },
    async leaveGroup() {
      if (current() !== "paused") {
        setParticipation("pausing");
        try { await service.pause(); } catch { /* stop is best effort; leave anyway */ }
        setParticipation("paused");
      }
      setGroupError(null);
      update({ group: null });
    },
  }), [service, saved, participation, controlError, hardware, refreshHardware, activity, update, preparing, groupError]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/** Processor cores to offer: the chosen share of this computer's threads, at least 1. */
export function cpusFor(cpuPercent: number, hardware: HardwareResult | null) {
  const threads = hardware?.status === "ok" ? hardware.hardware.threads : 2;
  return Math.max(1, Math.round((threads * cpuPercent) / 100));
}

export function useProvider() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useProvider must be used inside ProviderProvider");
  return ctx;
}
