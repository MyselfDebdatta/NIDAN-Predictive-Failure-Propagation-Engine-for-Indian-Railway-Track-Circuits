"""Model assurance, calibration, drift, and promotion gate models."""

from __future__ import annotations

from typing import Literal

from app.models.alerts import AlertLevel, FailureModeCode
from app.models.common import CamelModel, ModelVersions


class ModelRegistryEntry(CamelModel):
    """Registered model version metadata."""

    name: str
    version: str
    trained: str
    window: str
    owner: str
    state: str


class ReliabilityBin(CamelModel):
    """Calibration reliability bin (predicted vs observed rate)."""

    predicted: float
    observed: float
    n: int


class LevelCalibrationRow(CamelModel):
    """Calibration breakdown per alert level."""

    level: AlertLevel
    predicted: float
    observed: float
    n: int
    lead_time: str


class ModeMetricsRow(CamelModel):
    """Per-failure-mode precision/recall metrics."""

    code: FailureModeCode
    precision: float
    recall: float
    n: int


class DriftIndicator(CamelModel):
    """Population Stability Index (PSI) drift check."""

    name: str
    psi: float
    threshold: float
    state: Literal["nominal", "warning", "critical"]


class DataTrustFlagCount(CamelModel):
    """Count of assets carrying a specific data trust flag."""

    flag: str
    count: int


class DataTrustOverview(CamelModel):
    """Division-level data quality summary."""

    division: float
    low_trust_assets: int
    flags: list[DataTrustFlagCount]


class PromotionGate(CamelModel):
    """Automated shadow-to-active promotion gate check."""

    name: str
    rule: str
    value: str
    pass_: bool = False

    model_config = CamelModel.model_config.copy()


class ModelHealth(CamelModel):
    """Model health assurance snapshot matching modelHealthFixture."""

    as_of: str
    window: str
    ece: float
    ece_bins: int
    coverage: float
    held_out_n: int
    active_models: int
    drift_amber: int
    models: list[ModelRegistryEntry]
    reliability: list[ReliabilityBin]
    by_level: list[LevelCalibrationRow]
    by_mode: list[ModeMetricsRow]
    drift: list[DriftIndicator]
    data_trust: DataTrustOverview
    gates: list[dict[str, object]]
    signature: str
    model_versions: ModelVersions
    generated_at: str
