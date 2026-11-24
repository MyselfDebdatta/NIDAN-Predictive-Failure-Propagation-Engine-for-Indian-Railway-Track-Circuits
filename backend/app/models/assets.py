"""Asset, signal series, and failure-mode distribution models."""

from __future__ import annotations

from typing import Literal

from app.models.alerts import Alert, FailureModeCode
from app.models.common import CamelModel, ModelVersions


class AssetRecord(CamelModel):
    """Track-circuit asset register entry with provenance."""

    id: str
    length_m: int
    circuit_type: Literal["DC", "AC"]
    installed: str
    codal_life_years: int
    relay: str
    supply: str
    cable: str
    relay_room: str
    weather_cell: str
    provenance: str


class SignalSeries(CamelModel):
    """12-point daily telemetry series for a single asset signal."""

    key: str
    label: str
    unit: str
    baseline: float
    normal_band: str
    values: list[float]


class ModeRow(CamelModel):
    """Conformal failure-mode probability row for an asset."""

    code: FailureModeCode
    probability: float
    in_set: bool
    excluded: str | None = None


class AssetDetail(CamelModel):
    """Response for GET /v1/assets/{assetId}."""

    alert: Alert | None
    record: AssetRecord | None
    signals: list[SignalSeries]
    modes: list[ModeRow]
    model_versions: ModelVersions
    generated_at: str
