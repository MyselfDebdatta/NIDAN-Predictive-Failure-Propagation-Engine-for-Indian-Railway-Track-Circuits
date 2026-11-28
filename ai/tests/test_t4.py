"""Phase A5 tests: frailty survival, censoring, conformal RUL, calibration, and monotonicity."""

from __future__ import annotations

import numpy as np
import pytest

from nidan_ai.eval.metrics import expected_calibration_error
from nidan_ai.models.conformal import HorizonCalibrator, monotone_projection
from nidan_ai.models.survival import (
    CoxWeibull,
    build_survival_corpus,
    c_index,
    rul_interval,
    train_survival_model,
)

_SURVIVAL_SCENARIOS = (
    "monsoon-60d",
    "monsoon-fast",
    "relay-ageing",
    "cable-ingress",
    "supply-sag",
    "nff-flicker",
)


def test_c_index_and_censoring_on_synthetic_fixture() -> None:
    # Right-censored asset at t=50 with high duration and lower risk must be comparable
    # against an earlier failure at t=10 with higher risk.
    risks = np.array([2.0, 1.0, 0.2])
    durations = np.array([10.0, 25.0, 50.0])
    events = np.array([1, 1, 0])
    assert c_index(risks, durations, events) == pytest.approx(1.0)


def test_monotone_projection_and_pooled_calibration_fallback() -> None:
    projected = monotone_projection({"h24": 0.62, "h72": 0.40, "h7d": 0.35})
    assert projected["h24"] <= projected["h72"] <= projected["h7d"]
    assert 0.0 <= projected["h24"] <= 1.0

    # Calibration set smaller than 40 per zone must fall back to pooled calibration
    rng = np.random.default_rng(42)
    n = 50
    raw_h24 = rng.uniform(0.0, 0.4, n)
    raw_h72 = np.clip(raw_h24 + 0.15, 0.0, 1.0)
    raw_h7d = np.clip(raw_h72 + 0.15, 0.0, 1.0)
    outcomes = {
        "h24": (rng.random(n) < raw_h24).astype(float),
        "h72": (rng.random(n) < raw_h72).astype(float),
        "h7d": (rng.random(n) < raw_h7d).astype(float),
    }
    zones = np.array(["ADRA"] * 25 + ["BKSC"] * 25)
    calibrator = HorizonCalibrator().fit(
        {"h24": raw_h24, "h72": raw_h72, "h7d": raw_h7d}, outcomes, zones
    )
    assert calibrator.by_zone == {}
    calibrated, used_pooled = calibrator.calibrate(
        {"h24": 0.3, "h72": 0.2, "h7d": 0.5}, zone="ADRA"
    )
    assert used_pooled is True
    assert calibrated["h24"] <= calibrated["h72"] <= calibrated["h7d"]


def test_t4_frailty_survival_rul_coverage_and_ece_gate() -> None:
    ds = build_survival_corpus(seeds=(42, 43, 44, 99), scenarios=_SURVIVAL_SCENARIOS)
    b1 = train_survival_model(ds, seed=42, test_seed=99)
    b2 = train_survival_model(ds, seed=42, test_seed=99)

    assert b1.c_index > b1.constant_hazard_c_index + 0.15
    assert 0.75 <= b1.coverage <= 0.85
    assert isinstance(b1.model, CoxWeibull)
    assert len(b1.model.frailty) >= 2

    # Determinism + ordered non-negative integer RUL bounds
    for vec, grp in zip(ds.vectors[:10], ds.groups[:10], strict=True):
        iv1 = rul_interval(b1, vec, group=str(grp))
        iv2 = rul_interval(b2, vec, group=str(grp))
        assert iv1 == iv2
        p10, med, p90 = iv1
        assert all(isinstance(v, int) for v in iv1)
        assert 0 <= p10 <= med <= p90

    # Per-zone calibration ECE <= 0.05 across all three horizons and monotone on every row
    cal_idx = np.flatnonzero(ds.seeds == 44)
    test_idx = np.flatnonzero(ds.seeds == 99)

    def _probs(indices: np.ndarray):
        probs: dict[str, list[float]] = {"h24": [], "h72": [], "h7d": []}
        ys: dict[str, list[int]] = {"h24": [], "h72": [], "h7d": []}
        for i in indices:
            vec = ds.vectors[i]
            grp = str(ds.groups[i])
            for h, d in (("h24", 1.0), ("h72", 3.0), ("h7d", 7.0)):
                probs[h].append(1.0 - b1.model.survival(vec, d, group=grp))
                ys[h].append(int(ds.events[i] == 1 and ds.durations[i] <= d))
        return (
            {k: np.array(v) for k, v in probs.items()},
            {k: np.array(v) for k, v in ys.items()},
        )

    pc, yc = _probs(cal_idx)
    pt, yt = _probs(test_idx)
    hc = HorizonCalibrator().fit(pc, yc, ds.groups[cal_idx])
    calibrated_rows = [
        hc.calibrate(
            {"h24": pt["h24"][i], "h72": pt["h72"][i], "h7d": pt["h7d"][i]},
            str(ds.groups[test_idx[i]]),
        )[0]
        for i in range(len(test_idx))
    ]
    for row in calibrated_rows:
        assert 0.0 <= row["h24"] <= row["h72"] <= row["h7d"] <= 1.0
    for h in ("h24", "h72", "h7d"):
        ece = expected_calibration_error(np.array([r[h] for r in calibrated_rows]), yt[h], bins=10)
        assert ece <= 0.05, f"Expected {h} ECE <= 0.05, got {ece:.4f}"
