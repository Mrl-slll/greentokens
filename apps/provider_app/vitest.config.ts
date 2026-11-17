import { defineConfig } from "vitest/config";

export default defineConfig({
  define: { __APP_VERSION__: JSON.stringify("0.0.0-test"), __PROVIDER_SERVER__: JSON.stringify("https://gt.example.com") },
  test: { environment: "jsdom", include: ["tests/**/*.test.tsx"] },
});
