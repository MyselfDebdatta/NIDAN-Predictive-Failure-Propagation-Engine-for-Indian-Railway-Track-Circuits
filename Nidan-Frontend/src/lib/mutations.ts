import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { toast } from "sonner";
import type { Alert } from "@/data/fixtures";
import { dataAdapter, type DeferRequest } from "@/lib/api";
import { nidanKeys } from "@/lib/queries";
import { draftEvidenceReview } from "@/lib/review.functions";
import type { ReviewRequest } from "@/lib/review";

/** Optimistic, reversible acknowledge/defer. Only workflow flags change — never risk, RUL, level or cluster membership. */
function usePatchAlerts() {
  const queryClient = useQueryClient();
  return async (ids: string[], patch: (alert: Alert) => Alert) => {
    await queryClient.cancelQueries({ queryKey: nidanKeys.alerts });
    const previous = queryClient.getQueryData<Alert[]>(nidanKeys.alerts);
    const previousSingles = ids.map(
      (id) => [id, queryClient.getQueryData<Alert>(nidanKeys.alert(id))] as const,
    );
    queryClient.setQueryData<Alert[]>(nidanKeys.alerts, (list) =>
      list?.map((a) => (ids.includes(a.id) ? patch(a) : a)),
    );
    ids.forEach((id) =>
      queryClient.setQueryData<Alert>(nidanKeys.alert(id), (a) => (a ? patch(a) : a)),
    );
    return () => {
      queryClient.setQueryData(nidanKeys.alerts, previous);
      previousSingles.forEach(([id, value]) =>
        queryClient.setQueryData(nidanKeys.alert(id), value),
      );
    };
  };
}

export function useAcknowledge() {
  const patch = usePatchAlerts();
  return useMutation({
    mutationFn: async ({ ids, undo }: { ids: string[]; undo?: boolean }) => {
      if (undo) return { acknowledged: true as const };
      await Promise.all(ids.map((id) => dataAdapter.acknowledgeAlert(id)));
      return { acknowledged: true as const };
    },
    onMutate: ({ ids, undo }) =>
      patch(ids, (a) => {
        const { acknowledged: _drop, ...rest } = a;
        return undo ? rest : { ...rest, acknowledged: true };
      }),
    onError: (_error, _vars, rollback) => {
      rollback?.();
      toast.error("Acknowledge failed — rolled back. Try again.");
    },
  });
}

export function useDefer() {
  const patch = usePatchAlerts();
  return useMutation({
    mutationFn: async ({ ids, request }: { ids: string[]; request: DeferRequest }) => {
      await Promise.all(ids.map((id) => dataAdapter.deferAlert(id, request)));
      return { deferred: true as const };
    },
    onMutate: ({ ids, request }) => patch(ids, (a) => ({ ...a, deferral: request })),
    onError: (_error, _vars, rollback) => {
      rollback?.();
      toast.error("Defer failed — rolled back. Try again.");
    },
  });
}

export function useUndefer() {
  const patch = usePatchAlerts();
  return useMutation({
    mutationFn: async (_ids: string[]) => ({ ok: true as const }),
    onMutate: (ids) =>
      patch(ids, (a) => {
        const { deferral: _drop, ...rest } = a;
        return rest;
      }),
  });
}

export function useDraftWorkOrder() {
  return useMutation({
    mutationFn: ({
      alertId,
      action,
      blockId,
    }: {
      alertId: string;
      action: string;
      blockId: string;
    }) => dataAdapter.draftWorkOrder(alertId, { action, blockId }),
  });
}

/** AI evidence review draft. Returns a typed result; failures arrive as { ok: false } with a plain message. */
export function useEvidenceReview() {
  const run = useServerFn(draftEvidenceReview);
  return useMutation({ mutationFn: (request: ReviewRequest) => run({ data: request }) });
}
