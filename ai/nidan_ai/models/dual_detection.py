"""T5 dual-detection consistency: is a degrading circuit masked by a parallel axle counter?

T5 is **off** when axle-counter events are unavailable; it is never faked. The rule layer
compares track-circuit occupancy with axle-counter occupancy and inspects abnormal drop-away
timing. A small deterministic discrepancy score is reported with the rule evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nidan_ai.data.features import FeatureVector


@dataclass(slots=True)
class DualDetectionResult:
    """T5 output for one asset at one snapshot."""

    enabled: bool
    masked: bool
    score: float
    reasons: list[str]


def assess_dual_detection(vector: FeatureVector, *, axle_available: bool) -> DualDetectionResult:
    """Evaluate the dual-detection rule layer."""
    if not axle_available:
        return DualDetectionResult(
            enabled=False,
            masked=False,
            score=0.0,
            reasons=["axle-counter stream unavailable; T5 off"],
        )
    mismatch = vector.get("axle_mismatch_rate_24h")
    drop_p95 = vector.get("drop_p95_ms")
    flicker = vector.get("flicker_rate_24h")
    score = float(
        np.clip(
            2.2 * mismatch
            + 0.25 * max(0.0, (drop_p95 - 400.0) / 400.0)
            + 0.05 * min(1.0, flicker / 4.0),
            0.0,
            1.0,
        )
    )
    reasons: list[str] = []
    if mismatch > 0.01:
        reasons.append(
            "track circuit reported clear while axle counter was occupied "
            f"in {mismatch:.1%} of samples"
        )
    if drop_p95 > 450.0:
        reasons.append(f"drop-away p95 {drop_p95:.0f} ms is above the 450 ms review band")
    if flicker > 1.0:
        reasons.append("repeated short flickers in the 24 h window")
    if not reasons:
        reasons.append("track-circuit and axle-counter occupancy agree")
    return DualDetectionResult(
        enabled=True,
        masked=bool(mismatch > 0.01 or score >= 0.45),
        score=score,
        reasons=reasons,
    )
