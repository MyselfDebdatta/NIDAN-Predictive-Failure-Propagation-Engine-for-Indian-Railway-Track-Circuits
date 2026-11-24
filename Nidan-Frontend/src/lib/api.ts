import {
  alertFixtures,
  assetRecords,
  blockFixtures,
  blockJobs,
  clusterFixtures,
  fieldSyncFixture,
  fieldTaskFixtures,
  kpiFixture,
  modeDistribution,
  modeDistributionByAsset,
  modelHealthFixture,
  signalFixturesByAsset,
  type Alert,
  type BlockJob,
  type BlockWindow,
  type Cluster,
  type FieldTask,
  type SignalSeries,
} from "@/data/fixtures";

/** Advisory API surface. There is deliberately no interlocking, signal, route or track-circuit command endpoint. */
export interface FieldObservation {
  idempotencyKey: string;
  taskId: string;
  finding: "confirmed" | "not-found" | "something-else";
  measurements: {
    relayCurrent: string;
    ballastConductance: string;
    cableInsulation: string;
    feedVoltage: string;
  };
  note: string;
  createdAt: string;
}

export interface DeferRequest {
  reason: string;
  reviewDate: string;
}

export interface AssetDetail {
  alert: Alert | null;
  record: (typeof assetRecords)[string] | null;
  signals: SignalSeries[];
  modes: typeof modeDistribution;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  traceId: string;
}

export class ApiProblem extends Error {
  constructor(public problem: ProblemDetails) {
    super(problem.detail);
  }
}

export interface DataAdapter {
  listAlerts(): Promise<Alert[]>;
  getAlert(id: string): Promise<Alert>;
  getAsset(id: string): Promise<AssetDetail>;
  getBlocks(): Promise<{ windows: BlockWindow[]; jobs: BlockJob[] }>;
  getModels(): Promise<typeof modelHealthFixture>;
  getClusters(): Promise<Cluster[]>;
  getKpis(): Promise<typeof kpiFixture>;
  getFieldTasks(): Promise<{ tasks: FieldTask[]; sync: typeof fieldSyncFixture }>;
  draftWorkOrder(
    alertId: string,
    details: { action: string; blockId: string },
  ): Promise<{ id: string; status: "draft" }>;
  acknowledgeAlert(alertId: string): Promise<{ acknowledged: true }>;
  deferAlert(alertId: string, request: DeferRequest): Promise<{ deferred: true }>;
  submitObservation(observation: FieldObservation): Promise<{ queued: true; receipt: string }>;
}

function endpoint(path: string) {
  const base = import.meta.env["VITE_API_BASE_URL"] ?? "";
  return `${base}${path}`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(endpoint(path), {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const problem = body as Partial<ProblemDetails> | null;
    throw new ApiProblem({
      type: problem?.type ?? "about:blank",
      title: problem?.title ?? "Request failed",
      status: response.status,
      detail: problem?.detail ?? `Request failed (${response.status})`,
      traceId: problem?.traceId ?? response.headers.get("traceparent") ?? "unknown",
    });
  }
  return response.json() as Promise<T>;
}

const findAlert = (id: string) => {
  const decoded = decodeURIComponent(id);
  return alertFixtures.find((item) => item.id === decoded || item.assetId === decoded) ?? null;
};

const mockAdapter: DataAdapter = {
  async listAlerts() {
    return alertFixtures;
  },
  async getAlert(id) {
    const alert = findAlert(id);
    if (!alert) {
      throw new ApiProblem({
        type: "urn:nidan:not-found",
        title: "Alert not found",
        status: 404,
        detail: "This alert is not in the demo dataset.",
        traceId: "demo-404",
      });
    }
    return alert;
  },
  async getAsset(id) {
    const decoded = decodeURIComponent(id);
    const alert = alertFixtures.find((item) => item.assetId === decoded) ?? null;
    if (!alert) {
      throw new ApiProblem({
        type: "urn:nidan:not-found",
        title: "Asset not found",
        status: 404,
        detail: `${decoded} is not in the demo dataset.`,
        traceId: "demo-404",
      });
    }
    return {
      alert,
      record: assetRecords[decoded] ?? null,
      signals: signalFixturesByAsset[decoded] ?? [],
      modes: modeDistributionByAsset[decoded] ?? [],
    };
  },
  async getBlocks() {
    return { windows: blockFixtures, jobs: blockJobs };
  },
  async getModels() {
    return modelHealthFixture;
  },
  async getClusters() {
    return clusterFixtures;
  },
  async getKpis() {
    return kpiFixture;
  },
  async getFieldTasks() {
    return { tasks: fieldTaskFixtures, sync: fieldSyncFixture };
  },
  async draftWorkOrder() {
    return { id: "SMMS-draft-2048", status: "draft" };
  },
  async acknowledgeAlert() {
    return { acknowledged: true };
  },
  async deferAlert() {
    return { deferred: true };
  },
  async submitObservation(observation) {
    return { queued: true, receipt: `rcpt-${observation.idempotencyKey.slice(0, 8)}` };
  },
};

const apiAdapter: DataAdapter = {
  listAlerts: () => requestJson("/v1/alerts"),
  getAlert: (id) => requestJson(`/v1/alerts/${encodeURIComponent(id)}`),
  getAsset: (id) => requestJson(`/v1/assets/${encodeURIComponent(id)}`),
  getBlocks: () => requestJson("/v1/blocks"),
  getModels: () => requestJson("/v1/models/health"),
  getClusters: () => requestJson("/v1/clusters"),
  getKpis: () => requestJson("/v1/summary"),
  getFieldTasks: () => requestJson("/v1/field/tasks"),
  draftWorkOrder: (alertId, details) =>
    requestJson("/v1/work-orders/draft", {
      method: "POST",
      body: JSON.stringify({ alertId, ...details }),
    }),
  acknowledgeAlert: (alertId) =>
    requestJson(`/v1/alerts/${encodeURIComponent(alertId)}/acknowledge`, { method: "POST" }),
  deferAlert: (alertId, request) =>
    requestJson(`/v1/alerts/${encodeURIComponent(alertId)}/defer`, {
      method: "POST",
      body: JSON.stringify(request),
    }),
  submitObservation: (observation) =>
    requestJson("/v1/field/observations", {
      method: "POST",
      headers: { "idempotency-key": observation.idempotencyKey },
      body: JSON.stringify(observation),
    }),
};

export const dataSource = import.meta.env["VITE_DATA_SOURCE"] === "api" ? "api" : "mock";
export const dataAdapter: DataAdapter = dataSource === "api" ? apiAdapter : mockAdapter;
