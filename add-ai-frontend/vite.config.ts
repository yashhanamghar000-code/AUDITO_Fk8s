import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  // Deployed as a plain Docker container running `node .output/server/index.mjs`
  // (see Dockerfile) — not Cloudflare Workers, so pin the Nitro preset to a
  // real Node HTTP server. Without this it silently defaults to
  // "cloudflare-module", which exports a Workers-style fetch handler with no
  // top-level listener — `node` loads it and exits immediately with no error.
  nitro: {
    preset: "node-server",
  },
  tanstackStart: {
    server: { entry: "server" },
  },
  // Pass vite server config nested or directly depending on your plugin version:
  vite: {
    server: {
      allowedHosts: true,
    },
  },
});