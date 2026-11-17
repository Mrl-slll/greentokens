import { Activity, Cpu, Power, Settings } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { ProviderProvider, useProvider } from "./hooks/useProvider";
import { createMockProviderService } from "./services/mockProviderService";
import { createLiveProviderService } from "./services/liveProviderService";
import { detectHardware as defaultDetectHardware, inDesktopApp, type HardwareDetector } from "./services/hardware";
import type { ProviderService } from "./services/ProviderService";
import { Logo } from "./components/Logo";
import { HardwareScreen } from "./screens/Hardware";
import { HomeScreen } from "./screens/Home";
import { ActivityScreen } from "./screens/Activity";
import { SettingsScreen } from "./screens/Settings";

type Screen = "home" | "hardware" | "activity" | "settings";

export default function App({ service, detectHardware = defaultDetectHardware }: { service?: ProviderService; detectHardware?: HardwareDetector }) {
  // Installed app: the real worker (connects outward to GreenTokens). Browser preview and tests: the clearly labeled mock.
  const svc = useMemo(() => service ?? (inDesktopApp() ? createLiveProviderService() : createMockProviderService()), [service]);
  return (
    <ProviderProvider service={svc} detectHardware={detectHardware}>
      <Shell />
    </ProviderProvider>
  );
}

function Shell() {
  const { participation, service } = useProvider();
  // VPN-style: after signing in, the first thing you see is the Connect button.
  const [screen, setScreen] = useState<Screen>("home");

  const nav: { id: Screen; label: string; icon: ReactNode }[] = [
    { id: "home", label: "Home", icon: <Power aria-hidden /> },
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
          Status: <strong>{participation === "active" ? "Connected" : participation === "paused" ? "Not connected" : participation === "starting" ? "Connecting…" : "Disconnecting…"}</strong>
          <span className="mt-1 block text-xs text-slate-400">Version {__APP_VERSION__}</span>
        </p>
      </aside>
      <div className="flex-1">
        <div role="note" className="border-b border-amber-200 bg-amber-50 px-6 py-2 text-sm text-amber-900">
          {service.mode === "live"
            ? <><strong>Preview.</strong> While connected, this computer can receive GreenTokens training jobs. Earnings aren't offered during the pilot.</>
            : <><strong>Demo version.</strong> Connecting and activity are simulated; no jobs run on this computer. Hardware details are real.</>}
        </div>
        <main className="mx-auto max-w-4xl px-6 py-8">
          {screen === "home" && <HomeScreen />}
          {screen === "hardware" && <HardwareScreen onContinue={() => setScreen("home")} />}
          {screen === "activity" && <ActivityScreen />}
          {screen === "settings" && <SettingsScreen onOpenLimits={() => setScreen("home")} />}
        </main>
      </div>
    </div>
  );
}
