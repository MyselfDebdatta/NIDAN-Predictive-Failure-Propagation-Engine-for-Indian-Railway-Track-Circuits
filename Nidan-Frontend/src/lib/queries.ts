import { queryOptions } from "@tanstack/react-query";
import { dataAdapter } from "@/lib/api";

export const nidanKeys = {
  all: ["nidan"] as const,
  alerts: ["nidan", "alerts"] as const,
  alert: (id: string) => ["nidan", "alert", id] as const,
  asset: (id: string) => ["nidan", "asset", id] as const,
  blocks: ["nidan", "blocks"] as const,
  models: ["nidan", "models"] as const,
  clusters: ["nidan", "clusters"] as const,
  kpis: ["nidan", "kpis"] as const,
  fieldTasks: ["nidan", "field-tasks"] as const,
};

export const alertsQuery = queryOptions({
  queryKey: nidanKeys.alerts,
  queryFn: () => dataAdapter.listAlerts(),
});
export const alertQuery = (id: string) =>
  queryOptions({ queryKey: nidanKeys.alert(id), queryFn: () => dataAdapter.getAlert(id) });
export const assetQuery = (id: string) =>
  queryOptions({ queryKey: nidanKeys.asset(id), queryFn: () => dataAdapter.getAsset(id) });
export const blocksQuery = queryOptions({
  queryKey: nidanKeys.blocks,
  queryFn: () => dataAdapter.getBlocks(),
});
export const modelsQuery = queryOptions({
  queryKey: nidanKeys.models,
  queryFn: () => dataAdapter.getModels(),
});
export const clustersQuery = queryOptions({
  queryKey: nidanKeys.clusters,
  queryFn: () => dataAdapter.getClusters(),
});
export const kpisQuery = queryOptions({
  queryKey: nidanKeys.kpis,
  queryFn: () => dataAdapter.getKpis(),
});
export const fieldTasksQuery = queryOptions({
  queryKey: nidanKeys.fieldTasks,
  queryFn: () => dataAdapter.getFieldTasks(),
});
