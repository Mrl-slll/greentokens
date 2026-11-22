// Public connection address only. Never put an API key or password in these files.
import { readFileSync, writeFileSync } from "node:fs";
const configFile = new URL("../provider-server.json", import.meta.url);
const tauriFile = new URL("../src-tauri/tauri.conf.json", import.meta.url);
const address = process.argv[2] || process.env.GT_PROVIDER_SERVER || JSON.parse(readFileSync(configFile, "utf8")).url;
const url = new URL(address);
if (url.username || url.password || url.search || url.hash || url.pathname !== "/" ||
    (url.protocol !== "https:" && !(url.protocol === "http:" && url.hostname === "127.0.0.1"))) {
  throw new Error("Provider server must be an HTTPS origin (HTTP is allowed only for 127.0.0.1 development).");
}
if (process.env.CI && url.protocol !== "https:") throw new Error("Installer builds require a public HTTPS server.");
writeFileSync(configFile, JSON.stringify({ url: url.origin }, null, 2) + "\n");
const tauri = JSON.parse(readFileSync(tauriFile, "utf8"));
tauri.app.security.csp = `default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src ipc: http://ipc.localhost ${url.origin}; form-action 'none'; base-uri 'self'`;
writeFileSync(tauriFile, JSON.stringify(tauri, null, 2) + "\n");
console.log("Provider app server address configured.");
