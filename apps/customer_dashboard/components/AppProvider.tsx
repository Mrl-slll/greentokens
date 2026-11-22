"use client";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { liveClient, type ApiClient, type Mode } from "@/lib/client";
import { createMockClient } from "@/lib/mockClient";
import { resetMockRecent } from "@/lib/recent";
import { DEV_USERS, type DevUser } from "@/lib/types";

type Ctx = { user: DevUser; setUser: (u: DevUser) => void; mode: Mode; setMode: (m: Mode) => void; client: ApiClient };
const C = createContext<Ctx | null>(null);
export const useApp = () => { const c = useContext(C); if (!c) throw new Error("AppProvider missing"); return c; };

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<DevUser>("alice");
  const [mode, setModeState] = useState<Mode>("mock"); // safe default: never silently hit the backend
  const [mock, setMock] = useState(() => createMockClient());
  useEffect(() => { // restore saved choices after mount (avoids hydration mismatch)
    try {
      const u = localStorage.getItem("gt.user"), m = localStorage.getItem("gt.mode");
      /* eslint-disable react-hooks/set-state-in-effect -- one-time post-mount read of localStorage (avoids SSR hydration mismatch) */
      if (u && (DEV_USERS as readonly string[]).includes(u)) setUserState(u as DevUser);
      if (m === "live" || m === "mock") setModeState(m);
      /* eslint-enable react-hooks/set-state-in-effect */
    } catch { /* ignore */ }
  }, []);
  const setUser = (u: DevUser) => { setUserState(u); try { localStorage.setItem("gt.user", u); } catch {} };
  const setMode = (m: Mode) => { setModeState(m); if (m === "mock") { setMock(createMockClient()); resetMockRecent(); } try { localStorage.setItem("gt.mode", m); } catch {} };
  const client = mode === "live" ? liveClient : mock;
  const value = useMemo(() => ({ user, setUser, mode, setMode, client }), [user, mode, client]);
  return <C.Provider value={value}>{children}</C.Provider>;
}
