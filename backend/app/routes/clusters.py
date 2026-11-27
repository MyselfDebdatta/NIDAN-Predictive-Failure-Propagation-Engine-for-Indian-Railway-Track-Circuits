"""Common-cause cluster endpoints."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth import NidanPrincipal, get_current_principal, require_operator_or_above
from app.cache import RedisCache
from app.models.clusters import Cluster, ClusterMergeRequest, ClusterMergeResponse
from app.models.common import ModelVersions, utc_now_iso
from app.routes.deps import get_cache, get_cluster_service
from app.services import ClusterService

router = APIRouter(prefix="/v1/clusters", tags=["clusters"])


def _cluster_divisions(cluster: dict) -> list[str]:
    return [m.split("/", 1)[0] for m in cluster.get("members", []) if "/" in m]


@router.get("", response_model=list[Cluster], response_model_by_alias=True)
async def list_clusters(
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
    service: Annotated[ClusterService, Depends(get_cluster_service)],
):
    """Return common-cause failure clusters with members derived from alert.clusterId."""
    response.headers["Cache-Control"] = "private, max-age=30"
    response.headers["X-NIDAN-Generated-At"] = utc_now_iso()
    response.headers["X-NIDAN-Model-Versions"] = json.dumps(
        ModelVersions().model_dump(by_alias=True)
    )
    clusters = await service.list_clusters()
    if principal.has_global_scope:
        return clusters
    return [
        c
        for c in clusters
        if not _cluster_divisions(c)
        or any(principal.can_access_division(div) for div in _cluster_divisions(c))
    ]


@router.post(
    "/{cluster_id}/merge",
    response_model=ClusterMergeResponse,
    response_model_by_alias=True,
)
async def merge_alerts_to_cluster(
    cluster_id: str,
    body: ClusterMergeRequest,
    response: Response,
    _principal: Annotated[NidanPrincipal, Depends(require_operator_or_above)],
    service: Annotated[ClusterService, Depends(get_cluster_service)],
    cache: Annotated[RedisCache, Depends(get_cache)],
):
    """Fold alerts into an existing common-cause cluster."""
    response.headers["Cache-Control"] = "no-store"
    result = await service.merge_cluster(cluster_id, body.alert_ids)
    await cache.invalidate_prefixes("alerts:", "summary:")
    return result
