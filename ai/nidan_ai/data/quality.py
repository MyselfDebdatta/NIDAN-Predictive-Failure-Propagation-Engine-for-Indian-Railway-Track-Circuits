"""Data-trust scoring using the backend's exact closed-set flags and formula.

The AI layer must not invent flag names. This module imports the backend's
``compute_data_trust`` and re-implements only the *detection* of the same conditions over
canonical series. Trust discounts rank; it never suppresses an alert.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from app.ingestion.qc import (  # type: ignore[import-not-found]
    GAP_THRESHOLD,
    MAX_FUTURE_SKEW,
    SIGNAL_BOUNDS,
    STUCK_RUN_THRESHOLD,
    compute_data_trust,
)

from nidan_ai.config import TRUST_FLAGS


@dataclass(slots=True)
class QualityResult:
    """Trust score and closed-set flags for one asset at one snapshot."""

    score: float
    flags: list[str]
    gap_count: int
    stuck_run_max: int
    interpolation_share: float
    finite_ratio: float


def _closed(flags: set[str]) -> list[str]:
    unknown = flags - TRUST_FLAGS
    if unknown:
        raise ValueError(f"Unknown data-trust flag(s): {sorted(unknown)}")
    return sorted(flags)


def assess_quality(
    *,
    timestamps: list[datetime],
    relay_ma: np.ndarray,
    feed_v: np.ndarray | None = None,
    as_of: datetime,
    clock_offset_minutes: int = 0,
    supplied_quality: np.ndarray | None = None,
    age_vs_signature_mismatch: bool = False,
    shunt_pattern_review: bool = False,
    predicted_cascade: bool = False,
) -> QualityResult:
    """Compute trust from the same conditions and penalties as the backend Stream QC."""
    flags: set[str] = set()
    if age_vs_signature_mismatch:
        flags.add("age_vs_signature_mismatch")
    if shunt_pattern_review:
        flags.add("shunt_pattern_review")
    if predicted_cascade:
        flags.add("predicted_cascade")

    values = np.asarray(relay_ma, dtype=float)
    finite = np.isfinite(values)
    finite_ratio = float(finite.mean()) if values.size else 0.0
    interpolation_share = 0.0
    if supplied_quality is not None and supplied_quality.size:
        interpolation_share = float(np.mean(np.asarray(supplied_quality) == 1))

    if abs(int(clock_offset_minutes)) > int(MAX_FUTURE_SKEW.total_seconds() // 60):
        flags.add("clock_skew")
    if any(timestamp - as_of > MAX_FUTURE_SKEW for timestamp in timestamps):
        flags.add("clock_skew")

    # Gaps: either a NaN run of >= 6 h or a >= 6 h interval between finite samples.
    gap_count = 0
    if timestamps:
        last_finite: datetime | None = None
        nan_run_start: datetime | None = None
        for index, timestamp in enumerate(timestamps):
            if finite[index]:
                if nan_run_start is not None:
                    if timestamp - nan_run_start >= GAP_THRESHOLD:
                        gap_count += 1
                    nan_run_start = None
                if last_finite is not None and timestamp - last_finite >= GAP_THRESHOLD:
                    gap_count += 1
                last_finite = timestamp
            elif nan_run_start is None:
                nan_run_start = timestamp
        if nan_run_start is not None and timestamps[-1] - nan_run_start >= GAP_THRESHOLD:
            gap_count += 1
    if gap_count > 0:
        flags.add("logger_gap_6h")

    # Stuck-value runs (>= 30 identical consecutive finite readings).
    stuck_run_max = 0
    run = 1
    for index in range(1, values.size):
        if finite[index] and finite[index - 1] and values[index] == values[index - 1]:
            run += 1
            stuck_run_max = max(stuck_run_max, run)
        else:
            run = 1
    if stuck_run_max >= STUCK_RUN_THRESHOLD:
        flags.add("stuck_value_run")

    # Physical plausibility, matching backend SIGNAL_BOUNDS.
    relay_bounds = SIGNAL_BOUNDS.get("relay_i")
    if relay_bounds is not None and np.any(
        finite & ((values < relay_bounds[0]) | (values > relay_bounds[1]))
    ):
        flags.add("shunt_pattern_review")
    if feed_v is not None:
        feed = np.asarray(feed_v, dtype=float)
        feed_bounds = SIGNAL_BOUNDS.get("feed_v")
        feed_finite = np.isfinite(feed)
        if feed_bounds is not None and np.any(
            feed_finite & ((feed < feed_bounds[0]) | (feed > feed_bounds[1]))
        ):
            flags.add("shunt_pattern_review")

    closed = _closed(flags)
    score = compute_data_trust(closed, gap_count=max(1, gap_count))
    return QualityResult(
        score=score,
        flags=closed,
        gap_count=gap_count,
        stuck_run_max=stuck_run_max,
        interpolation_share=interpolation_share,
        finite_ratio=finite_ratio,
    )


def trust_from_flags(flags: list[str], *, gap_count: int = 1) -> float:
    """Exact backend trust formula for a known flag list."""
    return compute_data_trust(_closed(set(flags)), gap_count=gap_count)
