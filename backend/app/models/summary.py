"""KPI summary, SMMS draft work order, search, and user identity models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.models.common import CamelModel, ModelVersions


class KpiMetric(CamelModel):
    """Numeric KPI card value and delta."""

    value: float
    delta: str


class QueueCounts(CamelModel):
    """Alert queue summary counts by severity."""

    open: int
    critical: int
    warning: int
    watch: int
    median_age_hours: float


class KpiSummary(CamelModel):
    """Response for GET /v1/summary matching kpiFixture."""

    open_alerts: KpiMetric
    critical_shift: KpiMetric
    cluster_adjusted: KpiMetric
    block_fit: KpiMetric
    queue: QueueCounts
    model_versions: ModelVersions
    generated_at: str


class WorkOrderDraftRequest(CamelModel):
    """Request body for POST /v1/work-orders/draft (draft only; never submits to SMMS)."""

    alert_id: str
    action: str = Field(min_length=3, max_length=500)
    block_id: str


class WorkOrderDraftResponse(CamelModel):
    """Response for POST /v1/work-orders/draft."""

    id: str
    status: Literal["draft"] = "draft"
    alert_id: str
    block_id: str
    advisory_only: bool = True
    model_versions: ModelVersions
    generated_at: str


class SearchHit(CamelModel):
    """Federated search hit across alerts, assets, clusters, and SMMS precedents."""

    kind: Literal["alert", "asset", "cluster", "smms"]
    id: str
    title: str
    subtitle: str
    href: str


class SearchResponse(CamelModel):
    """Response for GET /v1/search?q=."""

    query: str
    hits: list[SearchHit]
    model_versions: ModelVersions
    generated_at: str


class MeResponse(CamelModel):
    """Response for GET /v1/me describing role, division scope, and advisory capabilities."""

    user_id: str
    display_name: str
    role: Literal["operator", "maintainer", "dste", "service", "admin"]
    divisions: list[str]
    advisory_only: bool = True
    vital_command_capable: bool = False
    capabilities: list[str]
    model_versions: ModelVersions
    generated_at: str
