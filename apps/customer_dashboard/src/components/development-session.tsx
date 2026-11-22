"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import {
  createGreenTokensClient,
  type GreenTokensClient,
} from "@/lib/api/client";
import type { DevelopmentIdentity } from "@/lib/api/types";

type DevelopmentSession = {
  identity: DevelopmentIdentity;
  client: GreenTokensClient;
  selectIdentity: (identity: DevelopmentIdentity) => void;
};

const SessionContext = createContext<DevelopmentSession | null>(null);
const STORAGE_KEY = "greentokens:development-identity";
const CHANGE_EVENT = "greentokens:development-identity-changed";
let fallbackIdentity: DevelopmentIdentity = "alice";

function isIdentity(value: string | null): value is DevelopmentIdentity {
  return value === "alice" || value === "bob" || value === "admin";
}

function getIdentitySnapshot(): DevelopmentIdentity {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return isIdentity(saved) ? saved : fallbackIdentity;
  } catch {
    return fallbackIdentity;
  }
}

function subscribeToIdentity(notify: () => void): () => void {
  window.addEventListener("storage", notify);
  window.addEventListener(CHANGE_EVENT, notify);
  return () => {
    window.removeEventListener("storage", notify);
    window.removeEventListener(CHANGE_EVENT, notify);
  };
}

function ActiveDevelopmentSession({
  identity,
  children,
}: {
  identity: DevelopmentIdentity;
  children: ReactNode;
}) {
  const client = useMemo(() => createGreenTokensClient(identity), [identity]);

  useEffect(() => () => client.dispose(), [client]);

  const selectIdentity = useCallback(
    (next: DevelopmentIdentity) => {
      if (next === identity) return;
      fallbackIdentity = next;
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // Storage may be unavailable. Notify this tab even in that case.
      }
      // Abort in-flight work before any UI switches identities.
      client.dispose();
      window.dispatchEvent(new Event(CHANGE_EVENT));
    },
    [client, identity],
  );

  const session = useMemo(
    () => ({ identity, client, selectIdentity }),
    [identity, client, selectIdentity],
  );

  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function DevelopmentSessionProvider({ children }: { children: ReactNode }) {
  const identity = useSyncExternalStore(
    subscribeToIdentity,
    getIdentitySnapshot,
    () => null,
  );

  // Don't mount API-consuming children until the browser identity is known.
  if (identity === null) return null;

  return (
    <ActiveDevelopmentSession key={identity} identity={identity}>
      {children}
    </ActiveDevelopmentSession>
  );
}

export function useDevelopmentSession(): DevelopmentSession {
  const session = useContext(SessionContext);
  if (!session) throw new Error("DevelopmentSessionProvider is missing");
  return session;
}
