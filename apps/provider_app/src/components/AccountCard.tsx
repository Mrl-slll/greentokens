import { useState, type FormEvent } from "react";
import { useProvider } from "../hooks/useProvider";
import { Button } from "./ui";

export function AccountCard() {
  const { account, authenticate, signOut, authError, authenticating, preparing, participation, service } = useProvider();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const busy = authenticating || preparing || participation === "starting" || participation === "pausing";
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (mode === "signup" && password !== confirmation) { setError("Passwords do not match."); return; }
    setError("");
    const entered = password;
    setPassword(""); setConfirmation("");
    await authenticate(mode, username, entered);
  }
  return <section className="w-full rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm" aria-label="Provider account">
    {account ? <>
      <p className="font-medium">Signed in as {account.displayName}</p>
      <p className="mt-1 text-sm text-slate-600">Press Connect when you want to share this computer.</p>
      <Button className="mt-3" disabled={busy} onClick={() => void signOut()}>Sign out</Button>
    </> : <>
      <h2 className="font-semibold">{mode === "signup" ? "Create your provider account" : "Sign in to GreenTokens"}</h2>
      <p className="mt-1 text-sm text-slate-600">{mode === "signup" ? "Choose a username and password. No invitation needed." : "Use your provider account on each computer you want to connect."}</p>
      {service.mode === "mock" && <p className="mt-1 text-sm text-amber-800">Demo only: use made-up details. No account is created.</p>}
      <form onSubmit={(e) => void submit(e)} className="mt-4 space-y-3">
        <div><label htmlFor="provider-username" className="block text-sm font-medium">Username</label>
          <input id="provider-username" required minLength={3} maxLength={32} pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{2,31}" autoComplete="username" autoCapitalize="none" spellCheck={false}
            value={username} disabled={busy} onChange={(e) => setUsername(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2" /></div>
        <div><label htmlFor="provider-password" className="block text-sm font-medium">Password</label>
          <input id="provider-password" type="password" required minLength={12} maxLength={128} autoComplete={mode === "signup" ? "new-password" : "current-password"}
            value={password} disabled={busy} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2" /></div>
        {mode === "signup" && <div><label htmlFor="provider-confirm" className="block text-sm font-medium">Confirm password</label>
          <input id="provider-confirm" type="password" required minLength={12} maxLength={128} autoComplete="new-password"
            value={confirmation} disabled={busy} onChange={(e) => setConfirmation(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2" /></div>}
        {mode === "signup" && <p className="text-xs text-slate-500">Use at least 12 characters. Keep your password safe; password recovery is not available in this pilot.</p>}
        <div className="flex flex-wrap gap-2"><Button type="submit" variant="primary" disabled={busy}>{authenticating ? "Please wait..." : mode === "signup" ? "Create account" : "Sign in"}</Button>
          <Button disabled={busy} onClick={() => { setMode(mode === "login" ? "signup" : "login"); setPassword(""); setConfirmation(""); setError(""); }}>{mode === "login" ? "New here? Create account" : "Already have an account? Sign in"}</Button></div>
      </form>
      <p className="mt-3 text-xs text-slate-500">Sign in again after reopening the app. Your password is never saved by GreenTokens.</p>
    </>}
    {(error || authError) && <p role="alert" className="mt-3 text-sm text-red-800">{error || authError}</p>}
  </section>;
}
