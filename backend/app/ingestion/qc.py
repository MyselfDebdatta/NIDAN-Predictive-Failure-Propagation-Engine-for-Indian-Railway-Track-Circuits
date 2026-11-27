"""Deterministic Stream QC engine tagging sample quality (0/1/2) and trust flags.

Implements docs/AI-ML-Implementation-Spec.md §5.3–5.4:
  - quality = 0: measured
  - quality = 1: interpolated
  - quality = 2: suspect (out-of-range, clock skew, or stuck-value run >= 30)
  - dataTrust discounts rank via closed-set flags; it never suppresses alerts.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.ingestion.schemas import TelemetrySample

# Physical plausibility bounds per track-circuit signal key.
SIGNAL_BOUNDS: dict[str, tuple[float, float]] = {
    "relay_i": (0.0, 1000.0),  # mA
    "ballast_g": (0.0, 25.0),  # S/km
    "feed_v": (0.0, 250.0),  # V
    "cable_ir": (0.0, 1000.0),  # MOhm
}

STUCK_RUN_THRESHOLD = 30
GAP_THRESHOLD = timedelta(hours=6)
MAX_FUTURE_SKEW = timedelta(minutes=15)

_TRUST_PENALTIES: dict[str, float] = {
    "logger_gap_6h": 0.15,
    "stuck_value_run": 0.10,
    "age_vs_signature_mismatch": 0.10,
    "shunt_pattern_review": 0.05,
    "predicted_cascade": 0.05,
    "clock_skew": 0.10,
}


@dataclass(slots=True)
class QcBatchResult:
    """QC-annotated telemetry samples plus per-asset trust metadata."""

    samples: list[TelemetrySample]
    flags_by_asset: dict[str, list[str]]
    trust_by_asset: dict[str, float]


def compute_data_trust(flags: list[str], *, gap_count: int = 1) -> float:
    """Compute dataTrust.score in [0.05, 1.0] from closed-set QC flags."""
    penalty = 0.0
    for flag in set(flags):
        if flag == "logger_gap_6h":
            penalty += min(0.45, 0.15 * max(1, gap_count))
        else:
            penalty += _TRUST_PENALTIES.get(flag, 0.05)
    return round(max(0.05, 1.0 - penalty), 4)


def evaluate_sample_qc(
    samples: list[TelemetrySample],
    *,
    now: datetime | None = None,
) -> QcBatchResult:
    """Tag each sample with quality (0=measured, 1=interpolated, 2=suspect) and asset flags."""
    ref_now = now or datetime.now(UTC)
    by_series: dict[tuple[str, str], list[TelemetrySample]] = defaultdict(list)
    for sample in samples:
        by_series[(sample.asset_id, sample.signal_key)].append(sample)

    annotated: list[TelemetrySample] = []
    asset_flags: dict[str, set[str]] = defaultdict(set)
    asset_gaps: dict[str, int] = defaultdict(int)

    for (asset_id, signal_key), series in by_series.items():
        ordered = sorted(series, key=lambda s: s.observed_at)
        bounds = SIGNAL_BOUNDS.get(signal_key)
        prev_ts: datetime | None = None
        prev_val: float | None = None
        identical_run = 0

        for sample in ordered:
            computed_q = 0

            # 1. Non-finite or out-of-range physical values -> suspect
            if not math.isfinite(sample.value) or (
                bounds is not None and not (bounds[0] <= sample.value <= bounds[1])
            ):
                computed_q = 2
                asset_flags[asset_id].add("shunt_pattern_review")

            # 2. Future timestamp beyond tolerance -> suspect + clock_skew
            if sample.observed_at - ref_now > MAX_FUTURE_SKEW:
                computed_q = 2
                asset_flags[asset_id].add("clock_skew")

            # 3. Stuck-value detection (>= 30 consecutive identical values)
            if prev_val is not None and sample.value == prev_val:
                identical_run += 1
            else:
                identical_run = 1
            prev_val = sample.value

            if identical_run >= STUCK_RUN_THRESHOLD:
                computed_q = 2
                asset_flags[asset_id].add("stuck_value_run")

            # 4. Logger gap >= 6h
            if prev_ts is not None and (sample.observed_at - prev_ts) >= GAP_THRESHOLD:
                asset_flags[asset_id].add("logger_gap_6h")
                asset_gaps[asset_id] += 1
            prev_ts = sample.observed_at

            # Preserve caller-supplied worse quality (e.g. interpolated=1 or suspect=2)
            caller_q = sample.quality if sample.quality is not None else 0
            final_q = max(caller_q, computed_q)
            if final_q not in (0, 1, 2):
                final_q = 2

            annotated.append(
                sample.model_copy(update={"quality": final_q})  # type: ignore[arg-type]
            )

    flags_out = {k: sorted(v) for k, v in asset_flags.items()}
    trust_out = {
        asset_id: compute_data_trust(flags, gap_count=asset_gaps.get(asset_id, 1))
        for asset_id, flags in flags_out.items()
    }
    return QcBatchResult(
        samples=annotated,
        flags_by_asset=flags_out,
        trust_by_asset=trust_out,
    )
