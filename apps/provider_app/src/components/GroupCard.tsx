import { Copy, Loader2, Users } from "lucide-react";
import { useState } from "react";
import { useProvider } from "../hooks/useProvider";
import { GROUP_CODE_RE } from "../types/provider";
import { Button } from "./ui";

/** Set up, show or leave the private group this computer connects to. */
export function GroupCard() {
  const { group, preparing, groupError, createGroup, joinGroup, leaveGroup, participation } = useProvider();
  const [joining, setJoining] = useState(false);
  const [code, setCode] = useState("");
  const [copied, setCopied] = useState(false);
  const leaderIp = group ? GROUP_CODE_RE.exec(group.code)?.[1] : undefined;

  async function copy() {
    if (!group) return;
    try { await navigator.clipboard.writeText(group.code); setCopied(true); setTimeout(() => setCopied(false), 3000); }
    catch { setCopied(false); }
  }

  return (
    <section aria-label="Your group" className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left">
      <h2 className="flex items-center gap-2 font-semibold"><Users className="h-5 w-5 text-emerald-700" aria-hidden /> Your group</h2>

      {preparing && (
        <p role="status" className="mt-2 flex items-center gap-2 text-sm text-slate-700">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Preparing this computer… The first time takes a few minutes.
        </p>
      )}

      {!group && !preparing && !joining && (
        <>
          <p className="mt-1 text-sm text-slate-600">Connect computers on the same home or office network. One computer leads; the others join with its code.</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Button variant="primary" onClick={() => void createGroup()}>Start a group</Button>
            <Button onClick={() => setJoining(true)}>Join a group</Button>
          </div>
        </>
      )}

      {!group && !preparing && joining && (
        <form className="mt-3 space-y-2" onSubmit={(e) => { e.preventDefault(); void joinGroup(code).then((ok) => { if (ok) { setJoining(false); setCode(""); } }); }}>
          <label htmlFor="group-code" className="text-sm font-medium">Group code from the leader's computer</label>
          <input id="group-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="GT1-…" autoComplete="off" spellCheck={false}
            className="w-full rounded-xl border border-slate-300 px-3 py-2 font-mono text-sm" />
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={!code.trim()}>Join</Button>
            <Button onClick={() => { setJoining(false); setCode(""); }}>Cancel</Button>
          </div>
        </form>
      )}

      {group?.role === "host" && !preparing && (
        <div className="mt-2 space-y-2">
          <p className="text-sm text-slate-600">This computer leads the group. Share this code with the computers you want to join:</p>
          <div className="flex items-center gap-2">
            <code className="min-w-0 flex-1 break-all rounded-lg bg-slate-100 px-3 py-2 text-sm">{group.code}</code>
            <Button onClick={() => void copy()} aria-label="Copy group code"><Copy className="h-4 w-4" aria-hidden />{copied ? "Copied" : "Copy"}</Button>
          </div>
          <p className="text-xs text-slate-500">Keep it private: anyone with this code on your network can join. Press the power button to open the group.</p>
        </div>
      )}

      {group?.role === "member" && !preparing && (
        <p className="mt-2 text-sm text-slate-600">Joined the group led by <span className="font-mono">{leaderIp}</span>. Press the power button to connect.</p>
      )}

      {group && !preparing && (
        <button type="button" className="mt-3 text-sm font-medium text-slate-600 underline" onClick={() => void leaveGroup()}>
          {participation === "paused" ? "Leave this group" : "Disconnect and leave this group"}
        </button>
      )}

      {groupError && <p role="alert" className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{groupError}</p>}
    </section>
  );
}
