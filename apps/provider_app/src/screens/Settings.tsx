import { useState } from "react";
import { useProvider } from "../hooks/useProvider";
import { Button, Card, DemoBadge, Toggle } from "../components/ui";
import type { MockProviderService } from "../services/mockProviderService";

const isMac = typeof navigator !== "undefined" && /mac/i.test(navigator.platform);

export function SettingsScreen({ onOpenLimits }: { onOpenLimits(): void }) {
  const { account, preferences, savePreferences, reset, hardware, service, repairSetup, preparing, setupDone, setupNote, participation, authenticating } = useProvider();
  const mock = service.mode === "mock" ? (service as MockProviderService) : null;
  const [, rerender] = useState(0);
  const hostname = hardware?.status === "ok" ? hardware.hardware.hostname : "";
  const [name, setName] = useState(preferences.deviceName || hostname);
  const [nameSaved, setNameSaved] = useState(false);
  const [confirmSignOut, setConfirmSignOut] = useState(false);

  async function saveName() {
    const ok = await savePreferences({ ...preferences, deviceName: name.trim().slice(0, 60) });
    setNameSaved(ok !== null);
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Settings</h1>
      </header>

      <Card title="Account" badge={mock ? <DemoBadge /> : undefined}>
        <dl className="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-slate-500">Status</dt><dd>{account ? account.displayName : "Sign in or create an account on Home."}</dd>
          <dt className="text-slate-500">Device ID</dt><dd className="font-mono">{account?.deviceId ?? "–"}</dd>
        </dl>
        <p className="mt-3 text-sm text-slate-500">{mock ? "This preview simulates accounts." : "Sign out on Home. Your password and session are not saved on this computer."}</p>
      </Card>

      <Card title="This computer">
        <label htmlFor="device-name" className="font-medium">Device name</label>
        <p className="text-sm text-slate-500">Helps you recognise this computer if you share more than one.</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <input id="device-name" value={name} maxLength={60} placeholder="My computer" onChange={(e) => { setName(e.target.value); setNameSaved(false); }}
            className="min-w-0 flex-1 rounded-xl border border-slate-300 px-3 py-2" />
          <Button onClick={() => void saveName()} disabled={name.trim() === (preferences.deviceName || hostname)}>Save name</Button>
        </div>
        <p aria-live="polite" className="mt-2 text-sm text-emerald-800">{nameSaved && "Name saved on this computer."}</p>
      </Card>

      <Card title="Preferences">
        <div className="space-y-5">
          <Toggle id="autostart" label={isMac ? "Open when I log in to my Mac" : "Open when I sign in to Windows"} checked={false} disabled onChange={() => undefined}
            description="Off. Coming in a later version. GreenTokens never starts sharing on its own." />
          <Toggle id="notifications" label="Notifications" checked={preferences.notifications}
            description="Saved on this computer. The demo doesn't send notifications yet."
            onChange={(notifications) => void savePreferences({ ...preferences, notifications })} />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><p className="font-medium">Resource limits</p><p className="text-sm text-slate-500">Choose Light, Balanced or Maximum on the Home screen.</p></div>
            <Button onClick={onOpenLimits}>Go to Home</Button>
          </div>
        </div>
      </Card>

      <Card title="About">
        <dl className="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-slate-500">Version</dt><dd>{__APP_VERSION__} ({mock ? "demo" : "preview"})</dd>
        </dl>
        <h3 className="mt-4 font-medium">Uninstalling</h3>
        {isMac ? (
          <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm text-slate-700">
            <li>Quit GreenTokens Provider.</li>
            <li>Open <strong>Finder → Applications</strong>.</li>
            <li>Drag <strong>GreenTokens Provider</strong> to the Trash.</li>
          </ol>
        ) : (
          <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm text-slate-700">
            <li>Open the Windows <strong>Start</strong> menu and choose <strong>Settings</strong>.</li>
            <li>Go to <strong>Apps</strong> → <strong>Installed apps</strong>.</li>
            <li>Find <strong>GreenTokens Provider</strong>, select <strong>⋯</strong>, then <strong>Uninstall</strong>.</li>
          </ol>
        )}
      </Card>

      <Card title="Setup">
        <p className="text-sm text-slate-600">{setupDone ? (setupNote || "This computer is set up for GreenTokens jobs.") : "Setup runs automatically the first time you connect."}</p>
        <p className="mt-1 text-xs text-slate-500">Use Repair after updating your graphics driver, or if jobs fail to start. Disconnect first.</p>
        <Button className="mt-3" disabled={preparing || participation !== "paused"} onClick={() => void repairSetup()}>
          {preparing ? "Setting up… this can take several minutes" : "Repair setup"}
        </Button>
      </Card>

      <Card title="Reset">
        <p className="text-sm text-slate-600">Disconnects and clears this app's saved settings on this computer. You'll be asked to agree again on the next Connect.</p>
        {!confirmSignOut
          ? <Button variant="danger" className="mt-3" onClick={() => setConfirmSignOut(true)}>Reset app</Button>
          : (
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="danger" disabled={preparing || authenticating || participation === "starting" || participation === "pausing"} onClick={() => void reset()}>Yes, reset</Button>
              <Button onClick={() => setConfirmSignOut(false)}>Cancel</Button>
            </div>
          )}
      </Card>

      {mock && (
        <details className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm">
          <summary className="cursor-pointer font-medium">Demo options (for testing)</summary>
          <label className="mt-3 flex items-center gap-2"><input type="checkbox" className="accent-emerald-700" checked={mock.options.disconnected} onChange={(e) => { mock.options.disconnected = e.target.checked; rerender((n) => n + 1); }} /> Simulate GreenTokens being unreachable</label>
        </details>
      )}
    </div>
  );
}
