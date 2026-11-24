"""Common-cause cluster and propagation graph models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.models.common import CamelModel, ModelVersions


class ClusterDecision(CamelModel):
    """Recommended consolidated maintenance decision inside a cluster."""

    title: str
    assets: list[str]
    block_id: str | None = None


class SharedEdge(CamelModel):
    """Shared physical cause or infrastructure edge linking cluster assets."""

    kind: str
    id: str
    note: str


class PredictedCascadeRange(CamelModel):
    """Day window range for predicted cascade."""

    min: int
    max: int


class PredictedCascade(CamelModel):
    """Predicted downstream cascade target asset."""

    asset_id: str
    in_days: PredictedCascadeRange


class Cluster(CamelModel):
    """Common-cause cluster with members derived from alert.clusterId."""

    id: str
    title: str
    state: Literal["open", "monitoring", "closed"]
    summary: str
    alerts_folded: int
    decisions: list[ClusterDecision]
    saved_block_hours: float
    weather_cell: str
    shared_edges: list[SharedEdge]
    members: list[str]
    predicted_cascade: PredictedCascade | None = None


class ClusterMergeRequest(CamelModel):
    """Request body for POST /v1/clusters/{id}/merge."""

    alert_ids: list[str] = Field(min_length=1)


class ClusterMergeResponse(CamelModel):
    """Response for POST /v1/clusters/{id}/merge."""

    cluster: Cluster
    merged_alert_ids: list[str]
    model_versions: ModelVersions
    generated_at: str
