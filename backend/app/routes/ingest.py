"""Model-run publisher endpoint — receives atomic snapshot + risk assessments from ML workers.

POST /v1/ingest/model-run
  Requires: service or admin role (AUTH_MODE=oidc) or AUTH_MODE=dev (passthrough).
  Body: ModelRunPublishRequest — a full snapshot + list of risk assessments.
  Effect:
    1. Inserts model_run row.
    2. Inserts snapshot row.
    3. Upserts risk_assessment rows (new rows, never updates existing).
    4. Advances alert.current_assessment_id for each affected asset.
    5. Publishes alert.upserted / cluster.updated events to Redis.

This is an **advisory, non-vital** write path.  It only touches the NIDAN
advisory data platform (risk_assessment, snapshot, alert, cluster) and cannot
command interlocking, signals, routes, points, or track circuits.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from pydantic import Field

from app.auth import NidanPrincipal, require_service_role
from app.cache import RedisCache
from app.models.common import CamelModel, utc_now_iso
from app.routes.deps import get_alert_service, get_cache, get_stream_hub
from app.services import AlertService, StreamHub

router = APIRouter(prefix="/v1/ingest", tags=["ingest"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RiskAssessmentInput(CamelModel):
    """One risk assessment row to publish for an asset."""

    asset_id: str
    level: str = Field(pattern="^(critical|warning|watch)$")
    policy_rank: int = Field(ge=1)
    persistence: int = Field(ge=0)
    h24: float = Field(ge=0, le=1)
    h72: float = Field(ge=0, le=1)
    h7d: float = Field(ge=0, le=1)
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


class ModelRunPublishRequest(CamelModel):
    """Full atomic publish payload from a model-run worker."""

    snapshot_as_of: datetime
    snapshot_week: int = Field(ge=1, le=53)
    snapshot_label: str
    code_version: str
    input_watermark: datetime
    policy_version: str = "policy-2026.07"
    assessments: list[RiskAssessmentInput] = Field(min_length=1)


class ModelRunPublishResponse(CamelModel):
    """Confirmation of a successful model-run publish."""

    model_run_id: str
    snapshot_id: str
    assessments_written: int
    alerts_updated: int
    events_published: list[str]
    generated_at: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


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
    """Atomically write a model-run snapshot and publish invalidation events.

    Advisory, non-vital: writes only to risk_assessment, snapshot, and alert
    tables in the NIDAN advisory data platform.
    """
    response.headers["Cache-Control"] = "no-store"

    # Delegate to the repository's publish_model_run method.
    # MemoryRepository returns a stub; PostgresRepository executes the full
    # DB transaction.
    result = await alert_service.publish_model_run(body.model_dump(by_alias=True))
    await cache.invalidate_prefixes("alerts:", "summary:", "models:")

    # Publish invalidation events to Redis for every updated alert
    events_published: list[str] = []
    for asset_id in result.get("updated_asset_ids", []):
        event = {
            "type": "alert.upserted",
            "assetId": asset_id,
            "snapshotId": result.get("snapshot_id", ""),
        }
        await stream_hub.publish(event)
        events_published.append(f"alert.upserted:{asset_id}")

    if result.get("clusters_updated"):
        for cluster_id in result["clusters_updated"]:
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
        generated_at=utc_now_iso(),
    )
