import { useEffect, useState } from "react";
import { readLiveUsage } from "../services/usage";
import type { LiveUsage } from "../types/provider";

const HISTORY = 60;

/** Polls real usage once a second while `enabled` (e.g. only while a screen that shows it is open). */
export function useLiveUsage(enabled: boolean) {
  const [usage, setUsage] = useState<LiveUsage | null>(null);
  const [history, setHistory] = useState<number[]>([]);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    const sample = async () => {
      const next = await readLiveUsage();
      if (!alive) return;
      if (!next) {
        setUnavailable(true);
        return;
      }
      setUnavailable(false);
      setUsage(next);
      if (!next.warmingUp) setHistory((h) => [...h.slice(-(HISTORY - 1)), next.greentokensCpuPercent]);
    };
    void sample();
    const id = setInterval(() => void sample(), 1000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [enabled]);

  return { usage, history, unavailable };
}
