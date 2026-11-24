"""Common-cause cluster endpoints."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.models.clusters import Cluster, ClusterMergeRequest, ClusterMergeResponse
from app.models.common import ModelVersions, utc_now_iso
from app.routes.deps import get_cluster_service
from app.services import ClusterService

router = APIRouter(prefix="/v1/clusters", tags=["clusters"])


@router.get("", response_model=list[Cluster], response_model_by_alias=True)
async def list_clusters(
    response: Response,
    service: Annotated[ClusterService, Depends(get_cluster_service)],
):
    """Return common-cause failure clusters with members derived from alert.clusterId."""
    response.headers["Cache-Control"] = "private, max-age=30"
    response.headers["X-NIDAN-Generated-At"] = utc_now_iso()
    response.headers["X-NIDAN-Model-Versions"] = json.dumps(
        ModelVersions().model_dump(by_alias=True)
    )
    return await service.list_clusters()


@router.post(
    "/{cluster_id}/merge",
    response_model=ClusterMergeResponse,
    response_model_by_alias=True,
)
async def merge_alerts_to_cluster(
    cluster_id: str,
    body: ClusterMergeRequest,
    response: Response,
    service: Annotated[ClusterService, Depends(get_cluster_service)],
):
    """Fold alerts into an existing common-cause cluster."""
    response.headers["Cache-Control"] = "no-store"
    return await service.merge_cluster(cluster_id, body.alert_ids)
