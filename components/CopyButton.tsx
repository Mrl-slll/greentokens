"use client";
import { useState } from "react";

/** Copies a code block's text (for Git and setup commands). */
export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }
        catch { setCopied(false); }
      }}
      className="absolute right-2 top-2 rounded border border-neutral-300 bg-white px-2 py-0.5 text-xs text-neutral-700 hover:bg-neutral-100 focus-visible:outline-2 focus-visible:outline-emerald-700"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
