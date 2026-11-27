"""Phase 3 ingestion routes: telemetry QC intake and atomic model-run publishing.

POST /v1/ingest/telemetry
  Requires: service or admin role (AUTH_MODE=oidc) or AUTH_MODE=dev passthrough.
  Accepts canonical TelemetryBatchRequest, C-DOT CCSP m2m:cin, or RDSO RDPMS frames,
  runs deterministic Stream QC (quality 0/1/2 + dataTrust flags), and persists to
  telemetry_reading.

POST /v1/ingest/model-run
  Requires: service or admin role (AUTH_MODE=oidc) or AUTH_MODE=dev passthrough.
  Atomically writes model_run, snapshot, clusters, risk_assessment rows, advances
  alert.current_assessment_id (or opens new alerts), optionally updates
  model_health_snapshot, and publishes Redis invalidation events.

Advisory, non-vital: no endpoint here writes to interlocking, signals, routes,
points, or track-circuit hardware.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from pydantic import Field, model_validator

from app.auth import NidanPrincipal, require_service_role
from app.cache import RedisCache
from app.connectors.smms import SmmsReadSyncAdapter, SmmsSyncRequest, SmmsSyncResponse
from app.ingestion.schemas import TelemetryIngestResponse
from app.ingestion.worker import TelemetryIngestProcessor
from app.models.common import CamelModel, utc_now_iso
from app.routes.deps import get_alert_service, get_cache, get_stream_hub
from app.services import AlertService, StreamHub

router = APIRouter(prefix="/v1/ingest", tags=["ingest"])

_MODE_RE = re.compile(r"^F(?:[1-9]|1[0-2])$")


class RiskAssessmentInput(CamelModel):
    """One risk assessment row to publish for an asset."""

    asset_id: str
    level: str = Field(pattern="^(critical|warning|watch)$")
    policy_rank: int = Field(ge=1)
    persistence: int = Field(ge=0)
    h24: float = Field(ge=0, le=1)
    h72: float = Field(ge=0, le=1)
    h7d: float = Field(ge=0, le=1, alias="h7d")
    ece_zone: float = Field(ge=0, le=1)
    p10_days: int = Field(ge=0)
    median_days: int = Field(ge=0)
    p90_days: int = Field(ge=0)
    rul_coverage: float = Field(ge=0, le=1)
    held_out_n: int = Field(ge=0)
    likely_modes: list[str] = Field(min_length=1, max_length=3)
    mode_probability: float = Field(ge=0, le=1)
    mode_set_coverage: float = Field(ge=0, le=1)
    data_trust_score: float = Field(ge=0, le=1)
    data_trust_flags: list[str] = Field(default_factory=list)
    cluster_root: bool = False
    block_window_id: str | None = None
    block_fit: str | None = None
    block_minutes: int | None = None
    cluster_id: str | None = None
    explanation: dict[str, Any] = Field(default_factory=dict)
    ranking: dict[str, Any] = Field(default_factory=dict)
    model_versions: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime

    @model_validator(mode="after")
    def _validate_spec_invariants(self) -> RiskAssessmentInput:
        if not (self.h24 <= self.h72 <= self.h7d):
            raise ValueError("Risk horizons must satisfy h24 <= h72 <= h7d.")
        if not (self.p10_days <= self.median_days <= self.p90_days):
            raise ValueError("RUL quantiles must satisfy p10Days <= medianDays <= p90Days.")
        for mode in self.likely_modes:
            if not _MODE_RE.match(mode):
                raise ValueError(f"Invalid failure mode '{mode}'; expected F1..F12.")
        if self.level == "critical" and not (self.h24 > 0.5 or self.cluster_root):
            raise ValueError("critical level requires h24 > 0.5 or clusterRoot=true.")
        if self.level == "warning" and not (self.h72 > 0.3):
            raise ValueError("warning level requires h72 > 0.3.")
        if (self.block_window_id is None) != (self.block_fit is None):
            raise ValueError(
                "blockWindowId and blockFit must be provided together or both omitted."
            )
        return self


class ClusterUpsertInput(CamelModel):
    """Common-cause cluster record produced by the GNN stage."""

    id: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=3, max_length=200)
    state: Literal["open", "monitoring", "closed"] = "open"
    summary: str = Field(min_length=3, max_length=500)
    weather_cell: str | None = None
    saved_block_hours: float = Field(default=0.0, ge=0.0)
    predicted_cascade_asset: str | None = None
    cascade_min_days: int | None = None
    cascade_max_days: int | None = None
    shared_edges: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)


class ModelRunPublishRequest(CamelModel):
    """Full atomic publish payload from a model-run worker."""

    snapshot_as_of: datetime
    snapshot_week: int = Field(ge=1, le=53)
    snapshot_label: str
    code_version: str
    input_watermark: datetime
    policy_version: str = "policy-2026.07"
    params: dict[str, Any] = Field(default_factory=dict)
    dataset_hash: str | None = None
    clusters: list[ClusterUpsertInput] = Field(default_factory=list)
    model_health: dict[str, Any] | None = None
    assessments: list[RiskAssessmentInput] = Field(min_length=1)


class ModelRunPublishResponse(CamelModel):
    """Confirmation of a successful (or idempotently replayed) model-run publish."""

    model_run_id: str
    snapshot_id: str
    assessments_written: int
    alerts_updated: int
    events_published: list[str]
    idempotent_replay: bool = False
    generated_at: str


@router.post(
    "/telemetry",
    response_model=TelemetryIngestResponse,
    response_model_by_alias=True,
)
async def ingest_telemetry(
    request: Request,
    response: Response,
    _principal: Annotated[NidanPrincipal, Depends(require_service_role)],
    stream_hub: Annotated[StreamHub, Depends(get_stream_hub)],
    cache: Annotated[RedisCache, Depends(get_cache)],
    payload: dict[str, Any] = Body(...),  # noqa: B008
    protocol: Annotated[
        Literal["canonical", "ccsp", "rdpms"] | None,
        Query(description="Override input envelope format (canonical | ccsp | rdpms)"),
    ] = None,
) -> TelemetryIngestResponse:
    """Normalize telemetry (canonical, C-DOT CCSP, or RDSO RDPMS), run Stream QC, and persist."""
    response.headers["Cache-Control"] = "no-store"
    detected: Literal["canonical", "ccsp", "rdpms"]
    if protocol is not None:
        detected = protocol
    elif "m2m:cin" in payload or "con" in payload:
        detected = "ccsp"
    elif "frames" in payload or ("stationCode" in payload and "signals" in payload):
        detected = "rdpms"
    else:
        detected = payload.get("sourceProtocol", "canonical")

    processor = TelemetryIngestProcessor(
        request.app.state.repo,
        stream_hub=stream_hub,
        cache=cache,
    )
    summary = await processor.process_raw(payload, protocol=detected)
    return TelemetryIngestResponse.model_validate(summary)


@router.post(
    "/model-run",
    response_model=ModelRunPublishResponse,
    response_model_by_alias=True,
)
async def publish_model_run(
    body: ModelRunPublishRequest,
    response: Response,
    _principal: Annotated[NidanPrincipal, Depends(require_service_role)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    stream_hub: Annotated[StreamHub, Depends(get_stream_hub)],
    cache: Annotated[RedisCache, Depends(get_cache)],
) -> ModelRunPublishResponse:
    """Atomically write a model-run snapshot and publish invalidation events."""
    response.headers["Cache-Control"] = "no-store"

    result = await alert_service.publish_model_run(body.model_dump(by_alias=True))
    is_replay = bool(result.get("idempotent_replay", False))
    events_published: list[str] = []

    if not is_replay:
        await cache.invalidate_prefixes("alerts:", "summary:", "models:", "assets:")

        for asset_id in result.get("updated_asset_ids", []):
            event = {
                "type": "alert.upserted",
                "assetId": asset_id,
                "snapshotId": result.get("snapshot_id", ""),
            }
            await stream_hub.publish(event)
            events_published.append(f"alert.upserted:{asset_id}")

        for cluster_id in result.get("clusters_updated", []):
            await stream_hub.publish({"type": "cluster.updated", "clusterId": cluster_id})
            events_published.append(f"cluster.updated:{cluster_id}")

        await stream_hub.publish(
            {
                "type": "model.promoted",
                "version": body.code_version,
                "snapshotId": result.get("snapshot_id", ""),
            }
        )
        events_published.append(f"model.promoted:{body.code_version}")

    return ModelRunPublishResponse(
        model_run_id=result.get("model_run_id", ""),
        snapshot_id=result.get("snapshot_id", ""),
        assessments_written=result.get("assessments_written", 0),
        alerts_updated=result.get("alerts_updated", 0),
        events_published=events_published,
        idempotent_replay=is_replay,
        generated_at=utc_now_iso(),
    )


@router.post(
    "/smms-sync",
    response_model=SmmsSyncResponse,
    response_model_by_alias=True,
)
async def sync_smms_read_only(
    body: SmmsSyncRequest,
    request: Request,
    response: Response,
    _principal: Annotated[NidanPrincipal, Depends(require_service_role)],
    cache: Annotated[RedisCache, Depends(get_cache)],
) -> SmmsSyncResponse:
    """One-way read-only CRIS SMMS sync (asset register + confirmed failure precedents)."""
    response.headers["Cache-Control"] = "no-store"
    adapter = SmmsReadSyncAdapter(request.app.state.repo, cache=cache)
    return await adapter.sync(body)
