"""Phase A1 physics twin tests: transmission line, UKF, and Appendix C checks."""

from __future__ import annotations

import numpy as np
import pytest

from nidan_ai.physics.line import (
    LineParams,
    dry_current,
    invert_ballast,
    relay_current,
    relay_margin_ratio,
    relay_percent_of_dry,
    voltage_current_profile,
)
from nidan_ai.physics.twin import estimate_snapshot, run_twin


def test_analytic_dry_circuit_matches_closed_form() -> None:
    params = LineParams()
    expected = params.feed_v / (
        params.source_ohm + params.rail_ohm_km * params.length_km + params.relay_ohm
    )
    actual = dry_current(params)
    assert abs(actual - expected) / expected < 1e-9
    assert round(actual, 3) == pytest.approx(0.994, abs=1e-3)


def test_documented_ballast_sweep_and_monotonicity() -> None:
    params = LineParams()
    assert round(relay_percent_of_dry(params, 50.0), 1) == pytest.approx(96.7, abs=0.1)
    assert round(relay_percent_of_dry(params, 2.0), 1) == pytest.approx(53.9, abs=0.1)
    assert round(relay_percent_of_dry(params, 0.7), 1) == pytest.approx(28.8, abs=0.1)
    assert round(invert_ballast(70.0, params), 2) == pytest.approx(3.99, abs=0.02)
    assert round(invert_ballast(50.0, params), 2) == pytest.approx(1.71, abs=0.02)

    resistances = [50.0, 20.0, 10.0, 8.0, 6.0, 5.0, 4.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.7]
    margins = [relay_margin_ratio(params, rb) for rb in resistances]
    margin_losses = [1.0 - m for m in margins]
    assert all(
        left <= right for left, right in zip(margin_losses[:-1], margin_losses[1:], strict=True)
    )


def test_occupancy_collapses_relay_current_and_recovers_on_clear() -> None:
    params = LineParams()
    free_pct = relay_percent_of_dry(params, 8.0, occupied=False)
    occ_pct = relay_percent_of_dry(params, 8.0, occupied=True)
    assert free_pct > 75.0
    assert occ_pct < 25.0
    assert relay_percent_of_dry(params, 8.0, occupied=False) == pytest.approx(free_pct)


def test_voltage_current_profile_is_monotone_along_line() -> None:
    params = LineParams()
    profile = voltage_current_profile(params, 4.0, points=11)
    assert profile["x_km"][0] == pytest.approx(0.0)
    assert profile["x_km"][-1] == pytest.approx(params.length_km)
    assert np.all(np.diff(profile["voltage_v"]) <= 0.0)
    assert np.all(np.diff(profile["current_a"]) <= 0.0)


def test_appendix_c_inverse_recovery_within_10_4_percent() -> None:
    params = LineParams()
    dry_ma = 1000.0 * dry_current(params)
    rng = np.random.default_rng(7)
    t = np.arange(0, 61)
    frac = t / 60.0
    true_rb = 8.0 * (1.0 - frac) + 1.5 * frac
    obs_rb = true_rb * np.exp(rng.normal(0.0, 0.04, t.size))
    obs_pct = np.array([relay_percent_of_dry(params, r) for r in obs_rb]) + rng.normal(
        0.0, 0.4, t.size
    )
    checkpoints = [0, 10, 20, 26, 30, 40, 50, 59, 60]
    errs = []
    for day in checkpoints:
        est = estimate_snapshot(params, obs_pct[day] / 100.0 * dry_ma)["ballast_ohm_km"]
        errs.append(abs(est - true_rb[day]) / true_rb[day])
    assert 100.0 * max(errs) <= 10.45


def test_ukf_handles_missing_outliers_and_is_deterministic() -> None:
    params = LineParams()
    dry_ma = 1000.0 * dry_current(params)
    rbs = np.linspace(8.0, 2.5, 48)
    relay_ma = np.array([1000.0 * relay_current(params, float(rb)) for rb in rbs])
    feed_v = np.full(48, params.feed_v)

    # Inject missing values and a single wild outlier (e.g. shunt / logger glitch)
    relay_dirty = relay_ma.copy()
    relay_dirty[10:14] = np.nan
    relay_dirty[25] = 5.0 * dry_ma

    res1 = run_twin(params, relay_ma=relay_dirty, feed_v=feed_v)
    res2 = run_twin(params, relay_ma=relay_dirty, feed_v=feed_v)

    assert res1.missing_samples == 4
    assert res1.skipped_updates >= 1
    assert np.isfinite(res1.final_gb_ohm_km)
    assert res1.final_gb_ohm_km < 5.0
    assert np.array_equal(res1.gb_ohm_km, res2.gb_ohm_km, equal_nan=True)
    assert np.array_equal(res1.covariance, res2.covariance)
