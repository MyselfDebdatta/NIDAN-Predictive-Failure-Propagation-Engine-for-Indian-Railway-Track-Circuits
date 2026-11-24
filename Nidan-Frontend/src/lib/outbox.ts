import { openDB, type IDBPDatabase } from "idb";
import type { FieldObservation } from "@/lib/api";

/** Field observations are written locally first, keyed by an idempotency UUID, then drained on reconnect. */
const DB_NAME = "nidan-field";
const STORE = "outbox";
const DRAFTS = "drafts";

let dbPromise: Promise<IDBPDatabase> | null = null;

function db() {
  if (typeof indexedDB === "undefined") return null;
  dbPromise ??= openDB(DB_NAME, 1, {
    upgrade(database) {
      database.createObjectStore(STORE, { keyPath: "idempotencyKey" });
      database.createObjectStore(DRAFTS);
    },
  });
  return dbPromise;
}

export async function queueObservation(observation: FieldObservation) {
  const database = await db();
  if (!database) return;
  await database.put(STORE, observation);
}

export async function countQueued() {
  const database = await db();
  if (!database) return 0;
  return database.count(STORE);
}

export async function listQueued(): Promise<FieldObservation[]> {
  const database = await db();
  if (!database) return [];
  return database.getAll(STORE);
}

export async function removeQueued(key: string) {
  const database = await db();
  if (!database) return;
  await database.delete(STORE, key);
}

export async function saveDraft(taskId: string, draft: unknown) {
  const database = await db();
  if (!database) return;
  await database.put(DRAFTS, draft, taskId);
}

export async function loadDraft<T>(taskId: string): Promise<T | undefined> {
  const database = await db();
  if (!database) return undefined;
  return database.get(DRAFTS, taskId) as Promise<T | undefined>;
}

export interface DrainResult {
  sent: { idempotencyKey: string; receipt: string }[];
  remaining: number;
  failed: boolean;
}

let draining: Promise<DrainResult> | null = null;

/**
 * Sends queued observations oldest first. Each one leaves the outbox only after the server returns
 * a receipt; on the first failure the rest stay queued for the next reconnect. Concurrent calls
 * share one run, and the idempotency key makes a repeated send safe.
 */
export function drainOutbox(
  submit: (observation: FieldObservation) => Promise<{ receipt: string }>,
): Promise<DrainResult> {
  draining ??= (async () => {
    const queued = (await listQueued()).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
    const sent: DrainResult["sent"] = [];
    for (const observation of queued) {
      let receipt: string;
      try {
        ({ receipt } = await submit(observation));
      } catch {
        return { sent, remaining: queued.length - sent.length, failed: true };
      }
      await removeQueued(observation.idempotencyKey);
      sent.push({ idempotencyKey: observation.idempotencyKey, receipt });
    }
    return { sent, remaining: 0, failed: false };
  })().finally(() => {
    draining = null;
  });
  return draining;
}
