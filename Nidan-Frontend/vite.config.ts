// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - TanStack devtools (dev-only, first), tanstackStart, viteReact, tailwindcss, tsConfigPaths,
//     nitro (build-only using cloudflare as a default target), VITE_* env injection, @ path alias,
//     React/TanStack dedupe, error logger plugins, and sandbox detection (port/host/strictPort).
// Never set ssr.external or resolve.external: the Worker has no runtime module resolution, so
// the build fails. Never add compression (compressPublicAssets, vite-plugin-compression):
// hosting already compresses at the edge.
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import type { Plugin } from "vite";
import { VitePWA, type VitePWAOptions } from "vite-plugin-pwa";

// Offline support for the field app (Workbox generateSW). Registration happens only in
// src/lib/sw-register.ts, which refuses dev, iframes and Lovable preview hosts.
const pwaOptions: Partial<VitePWAOptions> = {
  strategies: "generateSW",
  filename: "sw.js",
  registerType: "autoUpdate",
  injectRegister: null,
  manifest: false,
  devOptions: { enabled: false },
  workbox: {
    // Hashed JS/CSS and icons are precached; HTML is server-rendered, so pages use runtime caching.
    globPatterns: ["**/*.{js,css,woff2,svg,ico}"],
    navigateFallback: null,
    cleanupOutdatedCaches: true,
    clientsClaim: true,
    skipWaiting: true,
    runtimeCaching: [
      {
        // Field pages: network first, cached copy when there is no signal. Never cache-first.
        urlPattern: ({ request, url }) =>
          request.mode === "navigate" &&
          (url.pathname === "/field" || url.pathname.startsWith("/field/")) &&
          !url.pathname.startsWith("/~oauth"),
        handler: "NetworkFirst",
        options: {
          cacheName: "nidan-field-pages",
          networkTimeoutSeconds: 4,
          expiration: { maxEntries: 40, maxAgeSeconds: 14 * 24 * 3600 },
          cacheableResponse: { statuses: [200] },
        },
      },
      {
        // Live API mode: field task list readable offline.
        urlPattern: ({ request, url }) =>
          request.method === "GET" && url.pathname.startsWith("/v1/field/"),
        handler: "NetworkFirst",
        options: {
          cacheName: "nidan-field-data",
          networkTimeoutSeconds: 4,
          expiration: { maxEntries: 20, maxAgeSeconds: 7 * 24 * 3600 },
          cacheableResponse: { statuses: [200] },
        },
      },
    ],
  },
};

// The client build writes to the hosting public dir, not the top-level outDir; point Workbox at it.
const pwaClientOutDir: Plugin = {
  name: "nidan-pwa-client-outdir",
  enforce: "pre",
  configResolved(config) {
    const clientOutDir = config.environments["client"]?.build.outDir;
    if (clientOutDir) pwaOptions.outDir = clientOutDir;
  },
};

export default defineConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
  plugins: [pwaClientOutDir, VitePWA(pwaOptions)],
});
