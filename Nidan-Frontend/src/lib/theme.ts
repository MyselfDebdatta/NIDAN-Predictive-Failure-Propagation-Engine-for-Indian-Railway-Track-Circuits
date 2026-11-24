import { useSyncExternalStore } from "react";

export type NidanTheme = "day" | "night";
export const THEME_STORAGE_KEY = "nidan-theme";

export function resolveTheme(savedTheme: string | null, prefersDark: boolean): NidanTheme {
  if (savedTheme === "day" || savedTheme === "night") return savedTheme;
  return prefersDark ? "night" : "day";
}

/**
 * Runs inline in <head> before first paint: saved choice, else prefers-color-scheme, else Night.
 * Kept as a string so it executes before any bundle loads.
 */
export const themeBootScript = `(function(){try{var s=localStorage.getItem("${THEME_STORAGE_KEY}");var t=s==="day"||s==="night"?s:(window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"day":"night");document.documentElement.setAttribute("data-theme",t);}catch(e){document.documentElement.setAttribute("data-theme","night");}})();`;

export function applyTheme(theme: NidanTheme) {
  document.documentElement.dataset["theme"] = theme;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    /* storage unavailable: theme still applies for this session */
  }
}

function subscribe(callback: () => void) {
  const observer = new MutationObserver(callback);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

export function useTheme(): NidanTheme {
  return useSyncExternalStore(
    subscribe,
    () => (document.documentElement.dataset["theme"] === "day" ? "day" : "night"),
    () => "night",
  );
}
