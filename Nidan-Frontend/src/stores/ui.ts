import { create } from "zustand";

export type Lang = "en" | "hi";
export const LANG_STORAGE_KEY = "nidan-lang";

/** UI-only state. Server data lives in TanStack Query, filters live in the URL. */
interface UiState {
  lang: Lang;
  paletteOpen: boolean;
  moreOpen: boolean;
  lastFocusedRowId: string | null;
  setLang: (lang: Lang) => void;
  setPaletteOpen: (open: boolean) => void;
  setMoreOpen: (open: boolean) => void;
  setLastFocusedRowId: (id: string | null) => void;
}

export const useUi = create<UiState>((set) => ({
  lang: "en",
  paletteOpen: false,
  moreOpen: false,
  lastFocusedRowId: null,
  setLang: (lang) => {
    try {
      window.localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch {
      /* ignore */
    }
    set({ lang });
  },
  setPaletteOpen: (paletteOpen) => set({ paletteOpen }),
  setMoreOpen: (moreOpen) => set({ moreOpen }),
  setLastFocusedRowId: (lastFocusedRowId) => set({ lastFocusedRowId }),
}));
