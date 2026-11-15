import { CalendarClock, Gauge, Hand, ShieldCheck } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useProvider } from "../hooks/useProvider";
import type { MockProviderService } from "../services/mockProviderService";
import { Button, StatusPill } from "../components/ui";
import { Logo } from "../components/Logo";

export function Welcome() {
  const { consent, setConsent, signIn, signingIn, signInError, service } = useProvider();
  const mock = service.mode === "mock" ? (service as MockProviderService) : null;
  const [, rerender] = useState(0);

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10">
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3"><Logo /><span className="text-xl font-semibold">GreenTokens Provider</span></div>
          <StatusPill tone="warn">Demo mode: not connected to GreenTokens</StatusPill>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <h1 className="text-3xl font-semibold">Share your computer's spare power</h1>
          <p className="mt-3 text-slate-600">GreenTokens helps people run computing jobs on computers that would otherwise sit idle. You stay in control of your computer at all times.</p>
          <ul className="mt-6 grid gap-4 sm:grid-cols-3">
            <Point icon={<Hand aria-hidden />} title="You choose when">Nothing runs until you press Start Computing.</Point>
            <Point icon={<Gauge aria-hidden />} title="You set limits">Pick how much processor and memory to share.</Point>
            <Point icon={<CalendarClock aria-hidden />} title="Pause anytime">One click stops new work.</Point>
          </ul>

          <div className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
            <p className="flex items-center gap-2 font-medium text-slate-900"><ShieldCheck className="h-4 w-4" aria-hidden /> Privacy and resource use</p>
            <p className="mt-2">This version is a <strong>demo</strong>. It does not run any jobs on your computer and does not send anything to GreenTokens. It reads basic hardware details (processor, memory, graphics and Windows version) only to show them to you.</p>
          </div>

          <label className="mt-6 flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1 h-4 w-4 accent-emerald-700" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>I understand that when sharing is on, my computer may use more electricity, run warmer and feel slower, and that I can pause at any time.</span>
          </label>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button variant="primary" disabled={!consent || signingIn} onClick={() => void signIn()} className="px-6 py-3 text-lg">
              {signingIn ? "Signing in…" : "Sign in (demo)"}
            </Button>
            {!consent && <span className="text-sm text-slate-500">Tick the box above to continue.</span>}
          </div>
          {signInError && <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{signInError}</p>}
        </section>

        {mock && (
          <details className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm">
            <summary className="cursor-pointer font-medium">Demo options (for testing)</summary>
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2"><input type="checkbox" className="accent-emerald-700" checked={mock.options.failSignIn} onChange={(e) => { mock.options.failSignIn = e.target.checked; rerender((n) => n + 1); }} /> Simulate a failed sign-in</label>
              <label className="flex items-center gap-2"><input type="checkbox" className="accent-emerald-700" checked={mock.options.disconnected} onChange={(e) => { mock.options.disconnected = e.target.checked; rerender((n) => n + 1); }} /> Simulate GreenTokens being unreachable</label>
            </div>
          </details>
        )}
      </div>
    </main>
  );
}

function Point({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <li className="rounded-xl border border-slate-200 p-4">
      <span className="text-emerald-700 [&>svg]:h-6 [&>svg]:w-6">{icon}</span>
      <p className="mt-2 font-medium">{title}</p>
      <p className="text-sm text-slate-600">{children}</p>
    </li>
  );
}
