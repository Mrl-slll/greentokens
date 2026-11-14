"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
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

export function DevelopmentSessionProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<DevelopmentIdentity>("alice");
  const client = useMemo(() => createGreenTokensClient(identity), [identity]);

  const selectIdentity = useCallback(
    (next: DevelopmentIdentity) => {
      if (next === identity) return;
      client.dispose();
      setIdentity(next);
    },
    [client, identity],
  );

  const session = useMemo(
    () => ({ identity, client, selectIdentity }),
    [identity, client, selectIdentity],
  );

  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function useDevelopmentSession(): DevelopmentSession {
  const session = useContext(SessionContext);
  if (!session) throw new Error("DevelopmentSessionProvider is missing");
  return session;
}
