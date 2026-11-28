"""Hand-computed fixture tests for evaluation metrics (spec Appendix A, §17)."""

from __future__ import annotations

import numpy as np
import pytest

from nidan_ai.eval.metrics import (
    average_precision,
    bootstrap_ci,
    brier_score,
    c_index,
    division_coverage_gap,
    division_interval_coverage_gap,
    expected_calibration_error,
    interval_coverage,
    macro_f1,
    population_stability_index,
    precision_at_k,
    set_coverage,
)


def test_hand_computed_calibration_and_ranking_metrics() -> None:
    preds = np.array([0.1, 0.2, 0.8, 0.9])
    outcomes = np.array([0.0, 0.0, 1.0, 1.0])
    # 2 bins: [0.1, 0.2] -> mean 0.15, obs 0.0; [0.8, 0.9] -> mean 0.85, obs 1.0
    assert expected_calibration_error(preds, outcomes, bins=2) == pytest.approx(0.15)
    # Brier: ((0.1)^2 + (0.2)^2 + (-0.2)^2 + (-0.1)^2) / 4 = 0.025
    assert brier_score(preds, outcomes) == pytest.approx(0.025)

    assert precision_at_k(preds, outcomes, k=2) == pytest.approx(1.0)
    assert average_precision(preds, outcomes.astype(int)) == pytest.approx(1.0)


def test_hand_computed_coverage_psi_c_index_and_macro_f1() -> None:
    assert interval_coverage(np.array([1, 5, 10]), np.array([4, 8, 12]), np.array([2, 9, 11])) == (
        pytest.approx(2.0 / 3.0)
    )
    assert set_coverage([["F1"], ["F3", "F5"]], ["F1", "F6"]) == pytest.approx(0.5)

    # C-index: 3 subjects: (d=10, e=1, r=0.9), (d=20, e=1, r=0.5), (d=30, e=0, r=0.1)
    # Comparable pairs: (0,1) concordant, (0,2) concordant, (1,2) concordant -> 1.0
    assert c_index(np.array([0.9, 0.5, 0.1]), np.array([10, 20, 30]), np.array([1, 1, 0])) == (
        pytest.approx(1.0)
    )
    # Reversed ordering -> 0.0
    assert c_index(np.array([0.1, 0.5, 0.9]), np.array([10, 20, 30]), np.array([1, 1, 0])) == (
        pytest.approx(0.0)
    )

    ref = np.linspace(0.0, 10.0, 100)
    assert population_stability_index(ref, ref) == pytest.approx(0.0, abs=1e-9)
    shifted = ref + 8.0
    assert population_stability_index(ref, shifted) > 0.20

    truth = np.array(["F1", "F1", "F3", "F3"])
    pred = np.array(["F1", "F3", "F3", "F3"])
    # F1: P=1, R=0.5 -> F1=2/3; F3: P=2/3, R=1 -> F1=4/5 => mean = (2/3 + 4/5)/2 = 11/15
    assert macro_f1(truth, pred, ["F1", "F3"]) == pytest.approx(11.0 / 15.0)

    lo, hi = bootstrap_ci(np.array([1.0, 2.0, 3.0, 4.0]), n_bootstrap=200, seed=42)
    assert 1.0 <= lo <= hi <= 4.0

    sets_div = [["F1"]] * 6 + [["F3"]] * 6
    labels_div = ["F1"] * 5 + ["F3"] + ["F3"] * 6
    divs = ["ADRA"] * 6 + ["BKSC"] * 6
    gap, by_div = division_coverage_gap(sets_div, labels_div, divs, min_support=5)
    assert by_div == pytest.approx({"ADRA": 5.0 / 6.0, "BKSC": 1.0})
    assert gap == pytest.approx(1.0 / 6.0)

    igap, iby = division_interval_coverage_gap(
        np.zeros(10), np.ones(10), np.array([0.5] * 9 + [2.0]), ["ADRA"] * 5 + ["BKSC"] * 5
    )
    assert iby == pytest.approx({"ADRA": 1.0, "BKSC": 0.8})
    assert igap == pytest.approx(0.2)
