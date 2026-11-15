import { Activity, Cpu, Power, Settings } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { ProviderProvider, useProvider } from "./hooks/useProvider";
import { createMockProviderService } from "./services/mockProviderService";
import { detectHardware as defaultDetectHardware, type HardwareDetector } from "./services/hardware";
import type { ProviderService } from "./services/ProviderService";
import { Logo } from "./components/Logo";
import { Welcome } from "./screens/Welcome";
import { HardwareScreen } from "./screens/Hardware";
import { ControlScreen } from "./screens/Control";
import { ActivityScreen } from "./screens/Activity";
import { SettingsScreen } from "./screens/Settings";

type Screen = "control" | "hardware" | "activity" | "settings";

export default function App({ service, detectHardware = defaultDetectHardware }: { service?: ProviderService; detectHardware?: HardwareDetector }) {
  const svc = useMemo(() => service ?? createMockProviderService(), [service]);
  return (
    <ProviderProvider service={svc} detectHardware={detectHardware}>
      <Shell />
    </ProviderProvider>
  );
}

function Shell() {
  const { account, participation } = useProvider();
  // A fresh sign-in starts on Hardware (Sign in → Detect hardware → Choose limits → Start).
  const [screen, setScreen] = useState<Screen>("hardware");

  if (!account) return <Welcome />;

  const nav: { id: Screen; label: string; icon: ReactNode }[] = [
    { id: "control", label: "Computing", icon: <Power aria-hidden /> },
    { id: "hardware", label: "My computer", icon: <Cpu aria-hidden /> },
    { id: "activity", label: "Activity", icon: <Activity aria-hidden /> },
    { id: "settings", label: "Settings", icon: <Settings aria-hidden /> },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 md:flex-row">
      <aside className="border-b border-slate-200 bg-white md:w-60 md:shrink-0 md:border-r md:border-b-0">
        <div className="flex items-center gap-2 px-5 py-4"><Logo size={30} /><span className="font-semibold">GreenTokens Provider</span></div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col">
          {nav.map((n) => (
            <button key={n.id} type="button" onClick={() => setScreen(n.id)} aria-current={screen === n.id ? "page" : undefined}
              className={`flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-left font-medium [&>svg]:h-5 [&>svg]:w-5 ${screen === n.id ? "bg-emerald-50 text-emerald-900" : "text-slate-700 hover:bg-slate-100"}`}>
              {n.icon}{n.label}
            </button>
          ))}
        </nav>
        <p className="hidden px-5 py-4 text-sm text-slate-600 md:block">
          Status: <strong>{participation === "active" ? "Available for jobs" : participation === "paused" ? "Paused" : participation === "starting" ? "Starting…" : "Pausing…"}</strong>
        </p>
      </aside>
      <div className="flex-1">
        <div role="note" className="border-b border-amber-200 bg-amber-50 px-6 py-2 text-sm text-amber-900">
          <strong>Demo version.</strong> Sign-in, computing and activity are simulated; no jobs run on this computer. Hardware details are real.
        </div>
        <main className="mx-auto max-w-4xl px-6 py-8">
          {screen === "control" && <ControlScreen />}
          {screen === "hardware" && <HardwareScreen onContinue={() => setScreen("control")} />}
          {screen === "activity" && <ActivityScreen />}
          {screen === "settings" && <SettingsScreen onOpenLimits={() => setScreen("control")} />}
        </main>
      </div>
    </div>
  );
}
