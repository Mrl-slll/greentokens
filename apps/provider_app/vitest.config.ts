import { defineConfig } from "vitest/config";

export default defineConfig({
<<<<<<< HEAD
  define: { __APP_VERSION__: JSON.stringify("0.0.0-test"), __PROVIDER_SERVER__: JSON.stringify("https://gt.example.com") },
=======
  define: { __APP_VERSION__: JSON.stringify("0.0.0-test") },
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
  test: { environment: "jsdom", include: ["tests/**/*.test.tsx"] },
});
