import { create } from "zustand";

/** Field outbox sync state. The outbox itself lives in IndexedDB (src/lib/outbox.ts). */
interface SyncState {
  online: boolean;
  queued: number;
  lastSync: string;
  setOnline: (online: boolean) => void;
  setQueued: (queued: number) => void;
  setLastSync: (lastSync: string) => void;
}

export const useSync = create<SyncState>((set) => ({
  online: true,
  queued: 3,
  lastSync: "13 Jul · 23:52 IST",
  setOnline: (online) => set({ online }),
  setQueued: (queued) => set({ queued }),
  setLastSync: (lastSync) => set({ lastSync }),
}));
