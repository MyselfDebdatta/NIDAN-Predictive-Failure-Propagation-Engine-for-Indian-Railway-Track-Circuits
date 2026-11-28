"""Re-export and validate the frozen backend contract.

The AI package deliberately does **not** duplicate the Pydantic models. It imports the
installed ``nidan-backend`` package (``pip install -e backend``) so a contract drift in the
backend fails CI here too. ``ai/tests/conftest.py`` adds ``../backend`` to ``sys.path`` as a
documented local-development fallback only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models import (  # type: ignore[import-not-found]
    Alert,
    AssetRecord,
    CamelModel,
    Cluster,
    Explanation,
    FailureModeCode,
    ModelExplanation,
    ModelHealth,
    ModelVersions,
    PhysicsExplanation,
    PhysicsStateItem,
    PrecedentItem,
    RankingInputs,
    RiskScores,
    Rul,
    ShapFeature,
)
from app.routes.ingest import (  # type: ignore[import-not-found]
    ClusterUpsertInput,
    ModelRunPublishRequest,
    ModelRunPublishResponse,
    RiskAssessmentInput,
)

from nidan_ai.config import (
    CLASSIFIER_VERSION,
    CONFORMAL_VERSION,
    GNN_VERSION,
    POLICY_VERSION,
    SURVIVAL_VERSION,
    TWIN_VERSION,
)

__all__ = [
    "Alert",
    "AssetRecord",
    "CamelModel",
    "Cluster",
    "ClusterUpsertInput",
    "Explanation",
    "FailureModeCode",
    "ModelExplanation",
    "ModelHealth",
    "ModelRunPublishRequest",
    "ModelRunPublishResponse",
    "ModelVersions",
    "PhysicsExplanation",
    "PhysicsStateItem",
    "PrecedentItem",
    "RankingInputs",
    "RiskAssessmentInput",
    "RiskScores",
    "Rul",
    "ShapFeature",
    "assessment_json",
    "build_assessment_payload",
    "build_cluster_payload",
    "build_publish_payload",
    "default_model_versions",
    "publish_payload_json",
    "validate_assessment",
    "validate_model_health",
    "validate_publish_payload",
]


def default_model_versions(
    *,
    code_version: str,
    params_hash: str,
    bench_version: str,
    bench_hash: str,
    seed: int,
    split: str,
) -> dict[str, Any]:
    """Build the modelVersions dictionary recorded on every assessment and health snapshot."""
    return {
        "twin": TWIN_VERSION,
        "gnn": GNN_VERSION,
        "survival": SURVIVAL_VERSION,
        "classifier": CLASSIFIER_VERSION,
        "conformal": CONFORMAL_VERSION,
        "codeVersion": code_version,
        "paramsHash": params_hash,
        "benchVersion": bench_version,
        "benchHash": bench_hash,
        "seed": int(seed),
        "split": split,
    }


def validate_assessment(payload: dict[str, Any]) -> RiskAssessmentInput:
    """Validate a single assessment row against the backend contract."""
    model = RiskAssessmentInput.model_validate(payload)
    if model.explanation:
        Explanation.model_validate(model.explanation)
    if model.ranking:
        ranking = RankingInputs.model_validate(model.ranking)
        expected = {
            "critical": model.h24,
            "warning": model.h72,
            "watch": model.h7d,
        }[model.level]
        if abs(ranking.calibrated_risk - expected) > 1e-6:
            raise ValueError(
                f"ranking.calibratedRisk ({ranking.calibrated_risk}) must equal "
                f"driving horizon ({model.level} -> {expected}) for asset {model.asset_id}"
            )
    return model


def validate_publish_payload(payload: dict[str, Any]) -> ModelRunPublishRequest:
    """Validate a complete publish payload against the backend contract.

    Rejects duplicate assetIds and validates every nested explanation/ranking/modelHealth
    structure so callers fail closed before any network call.
    """
    model = ModelRunPublishRequest.model_validate(payload)
    seen_assets: set[str] = set()
    for row in model.assessments:
        if row.asset_id in seen_assets:
            raise ValueError(f"Duplicate assetId in publish payload: {row.asset_id}")
        seen_assets.add(row.asset_id)
        if row.explanation:
            Explanation.model_validate(row.explanation)
        if row.ranking:
            ranking = RankingInputs.model_validate(row.ranking)
            expected = {
                "critical": row.h24,
                "warning": row.h72,
                "watch": row.h7d,
            }[row.level]
            if abs(ranking.calibrated_risk - expected) > 1e-6:
                raise ValueError(
                    f"ranking.calibratedRisk ({ranking.calibrated_risk}) must equal "
                    f"{expected} for level {row.level} on asset {row.asset_id}"
                )
    if model.model_health is not None:
        ModelHealth.model_validate(model.model_health)
    return model


def validate_model_health(payload: dict[str, Any]) -> ModelHealth:
    """Validate a ModelHealth snapshot against the backend contract."""
    return ModelHealth.model_validate(payload)


def build_assessment_payload(
    *,
    asset_id: str,
    level: str,
    policy_rank: int,
    persistence: int,
    h24: float,
    h72: float,
    h7d: float,
    ece_zone: float,
    p10_days: int,
    median_days: int,
    p90_days: int,
    rul_coverage: float,
    held_out_n: int,
    likely_modes: list[str],
    mode_probability: float,
    mode_set_coverage: float,
    data_trust_score: float,
    data_trust_flags: list[str],
    explanation: dict[str, Any],
    ranking: dict[str, Any],
    model_versions: dict[str, Any],
    computed_at: datetime | str,
    cluster_root: bool = False,
    cluster_id: str | None = None,
    block_window_id: str | None = None,
    block_fit: str | None = None,
    block_minutes: int | None = None,
) -> dict[str, Any]:
    """Construct and validate a camelCase RiskAssessmentInput dictionary."""
    raw = {
        "assetId": asset_id,
        "level": level,
        "policyRank": int(policy_rank),
        "persistence": int(persistence),
        "h24": round(float(h24), 4),
        "h72": round(float(h72), 4),
        "h7d": round(float(h7d), 4),
        "eceZone": round(float(ece_zone), 4),
        "p10Days": int(p10_days),
        "medianDays": int(median_days),
        "p90Days": int(p90_days),
        "rulCoverage": round(float(rul_coverage), 4),
        "heldOutN": int(held_out_n),
        "likelyModes": list(likely_modes),
        "modeProbability": round(float(mode_probability), 4),
        "modeSetCoverage": round(float(mode_set_coverage), 4),
        "dataTrustScore": round(float(data_trust_score), 4),
        "dataTrustFlags": list(data_trust_flags),
        "clusterRoot": bool(cluster_root),
        "clusterId": cluster_id,
        "blockWindowId": block_window_id,
        "blockFit": block_fit,
        "blockMinutes": block_minutes,
        "explanation": explanation,
        "ranking": ranking,
        "modelVersions": model_versions,
        "computedAt": computed_at,
    }
    return assessment_json(raw)


def build_cluster_payload(
    *,
    cluster_id: str,
    title: str,
    summary: str,
    state: str = "open",
    weather_cell: str | None = None,
    saved_block_hours: float = 0.0,
    predicted_cascade_asset: str | None = None,
    cascade_min_days: int | None = None,
    cascade_max_days: int | None = None,
    shared_edges: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construct and validate a camelCase ClusterUpsertInput dictionary."""
    model = ClusterUpsertInput.model_validate(
        {
            "id": cluster_id,
            "title": title,
            "state": state,
            "summary": summary,
            "weatherCell": weather_cell,
            "savedBlockHours": round(float(saved_block_hours), 2),
            "predictedCascadeAsset": predicted_cascade_asset,
            "cascadeMinDays": cascade_min_days,
            "cascadeMaxDays": cascade_max_days,
            "sharedEdges": shared_edges or [],
            "decisions": decisions or [],
        }
    )
    return model.model_dump(by_alias=True, mode="json")


def build_publish_payload(
    *,
    snapshot_as_of: datetime | str,
    snapshot_week: int,
    snapshot_label: str,
    code_version: str,
    input_watermark: datetime | str,
    params: dict[str, Any],
    dataset_hash: str,
    assessments: list[dict[str, Any]],
    clusters: list[dict[str, Any]] | None = None,
    model_health: dict[str, Any] | None = None,
    policy_version: str = POLICY_VERSION,
) -> dict[str, Any]:
    """Construct and validate a complete camelCase ModelRunPublishRequest dictionary."""
    raw = {
        "snapshotAsOf": snapshot_as_of,
        "snapshotWeek": int(snapshot_week),
        "snapshotLabel": snapshot_label,
        "codeVersion": code_version,
        "inputWatermark": input_watermark,
        "policyVersion": policy_version,
        "params": params,
        "datasetHash": dataset_hash,
        "clusters": clusters or [],
        "modelHealth": model_health,
        "assessments": assessments,
    }
    return publish_payload_json(raw)


def publish_payload_json(payload: dict[str, Any]) -> dict[str, Any]:
    """Serialize a publish payload exactly as the API expects (camelCase, JSON mode)."""
    model = validate_publish_payload(payload)
    return model.model_dump(by_alias=True, mode="json")


def assessment_json(payload: dict[str, Any]) -> dict[str, Any]:
    """Serialize one assessment exactly as the API expects (camelCase, JSON mode)."""
    model = validate_assessment(payload)
    return model.model_dump(by_alias=True, mode="json")
