import { fireEvent, screen } from "@testing-library/react";
import type { ProviderAuth } from "../src/services/providerAuth";
import { ProviderError } from "../src/services/ProviderService";

export const TEST_KEY = "gt_" + "a".repeat(30);
export const credentials = { username: "provider-one", password: "test-only-password-123", deviceId: "device-0001" };
export function fakeAuth(): ProviderAuth {
  let deviceId: string | null = null;
  return {
    async authenticate(_mode, credentials) { deviceId = credentials.deviceId; return { displayName: credentials.username, deviceId }; },
    connection() { if (!deviceId) throw new ProviderError("Please sign in first."); return { server: "https://gt.example.com", key: TEST_KEY, deviceId }; },
    async signOut() { deviceId = null; },
  };
}
export async function signIn() {
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: credentials.username } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: credentials.password } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByText("Signed in as provider-one");
}
