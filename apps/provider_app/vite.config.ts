import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import pkg from "./package.json" with { type: "json" };
<<<<<<< HEAD
import server from "./provider-server.json" with { type: "json" };
=======
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))

// Tauri serves the built dist/ folder; dev uses a fixed loopback port.
export default defineConfig({
  plugins: [react(), tailwindcss()],
<<<<<<< HEAD
  define: { __APP_VERSION__: JSON.stringify(pkg.version), __PROVIDER_SERVER__: JSON.stringify(server.url) },
  // Don't pick up the web app's postcss.config.mjs from a parent folder; Tailwind runs via its Vite plugin.
  css: { postcss: { plugins: [] } },
=======
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
  clearScreen: false,
  server: { host: "127.0.0.1", port: 1420, strictPort: true },
  build: { target: "es2022" },
});
