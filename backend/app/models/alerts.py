"""Alert, explanation, risk, and RUL Pydantic models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.models.blocks import AlertBlockInfo
from app.models.common import CamelModel, ModelVersions

AlertLevel = Literal["watch", "warning", "critical"]
AlertStatus = Literal["open", "acknowledged", "deferred", "closed"]
FailureModeCode = Literal["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]


class RiskScores(CamelModel):
    """Calibrated failure probability across 24 h, 72 h, and 7 d horizons."""

    h24: float = Field(ge=0.0, le=1.0)
    h72: float = Field(ge=0.0, le=1.0)
    h7d: float = Field(ge=0.0, le=1.0)
    ece_zone: float = Field(ge=0.0, le=1.0)


class Rul(CamelModel):
    """Conformal remaining-useful-life interval in days."""

    p10_days: int = Field(ge=0)
    median_days: int = Field(ge=0)
    p90_days: int = Field(ge=0)
    coverage: float = Field(ge=0.0, le=1.0)
    held_out_n: int = Field(ge=0)


class PhysicsStateItem(CamelModel):
    """Single physical observation vs baseline in the Physics tab."""

    label: str
    value: str
    baseline: str


class PhysicsExplanation(CamelModel):
    """First explanation lens: physical state and falsifier."""

    headline: str
    state: list[PhysicsStateItem]
    falsifier: str


class ShapFeature(CamelModel):
    """Top signed SHAP feature attribution."""

    feature: str
    label: str
    value: float


class ModelExplanation(CamelModel):
    """Second explanation lens: SHAP attributions and conformal mode set."""

    shap_top: list[ShapFeature]
    calibration_note: str
    mode_set: list[FailureModeCode]
    mode_set_coverage: float = Field(ge=0.0, le=1.0)
    agreement: str


class PrecedentItem(CamelModel):
    """Third explanation lens: similar historical SMMS event."""

    smms_id: str
    asset_id: str
    confirmed_mode: FailureModeCode
    similarity: float = Field(ge=0.0, le=1.0)
    days_ago: int = Field(ge=0)
    outcome: str


class Explanation(CamelModel):
    """Three-lens explanation attached to every alert."""

    physics: PhysicsExplanation
    model: ModelExplanation
    precedents: list[PrecedentItem]


class RankingInputs(CamelModel):
    """Server-computed ranking rationale inputs."""

    calibrated_risk: float = Field(ge=0.0, le=1.0)
    consequence: Literal["high", "medium", "low"]
    consequence_note: str
    exposure: str
    trust_discount: float = Field(ge=0.0, le=1.0)
    tie_breaker: str


class DataTrust(CamelModel):
    """Telemetry and metadata trust score with active diagnostic flags."""

    score: float = Field(ge=0.0, le=1.0)
    flags: list[str] = Field(default_factory=list)


class DeferralInfo(CamelModel):
    """Active deferral reason and scheduled review date."""

    reason: str
    review_date: str


class Alert(CamelModel):
    """Full alert domain object matching Nidan-Frontend Alert interface."""

    id: str
    asset_id: str
    asset_name: str
    route: str
    division: str
    level: AlertLevel
    policy_rank: int = Field(ge=1)
    persistence: int = Field(ge=0)
    risk: RiskScores
    rul: Rul
    likely_modes: list[FailureModeCode] = Field(min_length=1, max_length=3)
    mode_probability: float = Field(ge=0.0, le=1.0)
    mode_set_coverage: float = Field(ge=0.0, le=1.0)
    cluster_id: str | None = None
    data_trust: DataTrust
    block: AlertBlockInfo | None = None
    explanation: Explanation
    ranking: RankingInputs
    age_minutes: int = Field(ge=0)
    model_versions: ModelVersions
    acknowledged: bool | None = None
    deferral: DeferralInfo | None = None
    generated_at: str | None = None


class AssetExplanationResponse(CamelModel):
    """Response for GET /v1/assets/{assetId}/explanation."""

    alert_id: str
    asset_id: str
    physics: PhysicsExplanation
    model: ModelExplanation
    precedents: list[PrecedentItem]
    model_versions: ModelVersions
    generated_at: str


class AcknowledgeResponse(CamelModel):
    """Response for POST /v1/alerts/{id}/acknowledge."""

    acknowledged: bool = True
    alert_id: str
    status: AlertStatus = "acknowledged"
    model_versions: ModelVersions
    generated_at: str


class DeferRequest(CamelModel):
    """Request body for POST /v1/alerts/{id}/defer."""

    reason: str = Field(min_length=10, max_length=1000)
    review_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

    @model_validator(mode="after")
    def validate_trimmed_reason(self) -> DeferRequest:
        if len(self.reason.strip()) < 10:
            raise ValueError("Give a reason of at least 10 characters.")
        return self


class DeferResponse(CamelModel):
    """Response for POST /v1/alerts/{id}/defer."""

    deferred: bool = True
    alert_id: str
    status: AlertStatus = "deferred"
    deferral: DeferralInfo
    model_versions: ModelVersions
    generated_at: str
