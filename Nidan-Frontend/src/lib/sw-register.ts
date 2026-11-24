/**
 * The only place the app-shell service worker is registered. It never registers in dev, inside an
 * iframe, or on Lovable preview/editor hosts — stale workers there would serve old builds. In any
 * refused context, matching /sw.js registrations are removed. Add ?sw=off to any URL to unregister.
 */
const SW_PATH = "/sw.js";
const PREVIEW_LABEL = /^(?:id-preview|preview)(?:-[a-z0-9]+)?--.+$/;
const DEV_PROJECT_LABEL = /^project--[a-z0-9-]+-dev$/;
const LOVABLE_HOSTS = ["lovable.app", "gpt-eng.com", "gptengineer.run"];
const EDITOR_DOMAINS = ["lovableproject.com", "lovableproject-dev.com", "beta.lovable.dev"];

export type SwBlockReason =
  "dev" | "iframe" | "preview-host" | "kill-switch" | "unsupported" | null;

export function serviceWorkerBlockReason(input: {
  hostname: string;
  search: string;
  prod: boolean;
  inIframe: boolean;
  supported: boolean;
}): SwBlockReason {
  const host = input.hostname.toLowerCase();
  if (new URLSearchParams(input.search).get("sw") === "off") return "kill-switch";
  if (!input.supported) return "unsupported";
  if (!input.prod) return "dev";
  if (input.inIframe) return "iframe";
  const label = host.split(".")[0] ?? "";
  const onLovableHost = LOVABLE_HOSTS.some((domain) => host.endsWith(`.${domain}`));
  if (onLovableHost && (PREVIEW_LABEL.test(label) || DEV_PROJECT_LABEL.test(label)))
    return "preview-host";
  if (EDITOR_DOMAINS.some((domain) => host === domain || host.endsWith(`.${domain}`)))
    return "preview-host";
  return null;
}

async function unregisterAppWorkers() {
  const registrations = await navigator.serviceWorker.getRegistrations();
  await Promise.all(
    registrations
      .filter((r) =>
        [r.active, r.waiting, r.installing].some(
          (w) => w && new URL(w.scriptURL).pathname === SW_PATH,
        ),
      )
      .map((r) => r.unregister()),
  );
}

let started = false;

/** Call once from a useEffect. Resolves to true when the worker was registered. */
export async function setupServiceWorker() {
  if (started || typeof window === "undefined") return false;
  started = true;
  let inIframe = true;
  try {
    inIframe = window.self !== window.top;
  } catch {
    inIframe = true;
  }
  const supported = "serviceWorker" in navigator;
  const reason = serviceWorkerBlockReason({
    hostname: window.location.hostname,
    search: window.location.search,
    prod: import.meta.env.PROD,
    inIframe,
    supported,
  });
  if (reason) {
    if (supported) await unregisterAppWorkers().catch(() => undefined);
    return false;
  }
  const { registerSW } = await import("virtual:pwa-register");
  registerSW({ immediate: true });
  return true;
}

/** Field page cache shared with the Workbox NetworkFirst route in vite.config.ts. */
export const FIELD_PAGE_CACHE = "nidan-field-pages";

/**
 * Stores the field pages so they open without signal even if the technician has not visited
 * them yet. Only runs where the service worker is active.
 */
export async function warmFieldPages(paths: string[]) {
  if (
    typeof window === "undefined" ||
    !("caches" in window) ||
    !navigator.serviceWorker?.controller ||
    !navigator.onLine
  )
    return;
  const cache = await caches.open(FIELD_PAGE_CACHE);
  await Promise.all(
    paths.map(async (path) => {
      try {
        const response = await fetch(path, {
          credentials: "same-origin",
          headers: { accept: "text/html" },
        });
        if (response.ok) await cache.put(path, response);
      } catch {
        /* offline or blocked — the page is cached on its next visit */
      }
    }),
  );
}
