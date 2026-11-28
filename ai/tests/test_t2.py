"""Phase A3 tests: T2 fault diagnosis, conformal mode sets, SHAP determinism, non-leakage."""

from __future__ import annotations

import numpy as np
import pytest

from nidan_ai.config import RELEASE_MODES
from nidan_ai.data.features import FEATURE_LABELS, MODEL_FEATURES
from nidan_ai.explain.shap import signed_attribution
from nidan_ai.models.classifier import (
    build_mode_corpus,
    diagnose_with_set,
    train_diagnosis_model,
)
from nidan_ai.models.conformal import MondrianConformal, SplitConformal

_FAST_SCENARIOS = ("monsoon-60d", "rail-break-step", "relay-ageing", "supply-sag", "nff-flicker")


def test_t2_fast_release_modes_beat_baseline_and_shap_is_deterministic() -> None:
    corpus = build_mode_corpus(seeds=(42, 43, 99), scenarios=_FAST_SCENARIOS, snapshots_per_asset=3)
    bundle = train_diagnosis_model(corpus, seed=42, test_seed=99, alpha=0.10)

    assert set(bundle.classes).issubset(set(RELEASE_MODES))
    assert bundle.macro_f1 > bundle.baseline_macro_f1 + 0.25
    assert bundle.mean_set_size <= 3.0
    assert 0.80 <= bundle.coverage <= 0.98

    sample = corpus.vectors[0]
    diag1 = diagnose_with_set(bundle, sample, group=corpus.groups[0])
    diag2 = diagnose_with_set(bundle, sample, group=corpus.groups[0])
    assert diag1["likely_modes"] == diag2["likely_modes"]
    assert diag1["mode_set"] == diag2["mode_set"]
    assert 1 <= len(diag1["likely_modes"]) <= 3
    assert 1 <= len(diag1["mode_set"]) <= 3
    assert diag1["shap_top"] == diag2["shap_top"]
    assert 1 <= len(diag1["shap_top"]) <= 5

    # Human labels must come from FEATURE_LABELS, not raw internal-only column names
    for item in diag1["shap_top"]:
        assert item["feature"] in MODEL_FEATURES
        assert item["label"] == FEATURE_LABELS[item["feature"]]

    # Standalone signed_attribution matches classifier.shap_top
    via_shap = signed_attribution(bundle.classifier, sample, top_k=5)
    assert via_shap == diag1["shap_top"]


def test_conformal_wider_set_never_shrinks_and_no_label_leakage() -> None:
    probs = np.array(
        [
            [0.85, 0.10, 0.05],
            [0.70, 0.20, 0.10],
            [0.20, 0.65, 0.15],
            [0.15, 0.25, 0.60],
            [0.60, 0.30, 0.10],
            [0.10, 0.75, 0.15],
        ]
    )
    labels = np.array(["F1", "F1", "F3", "F5", "F1", "F3"])
    classes = ["F1", "F3", "F5"]
    strict = SplitConformal(alpha=0.20).fit(probs, labels, classes)
    wider = SplitConformal(alpha=0.05).fit(probs, labels, classes)
    for row in probs:
        assert len(wider.predict_set(row)) >= len(strict.predict_set(row))

    mc = MondrianConformal(alpha=0.10, min_group_size=3).fit(
        probs, labels, classes, ["ADRA"] * 3 + ["BKSC"] * 3
    )
    assert len(mc.predict_set(probs[0], "ADRA")) >= 1
    assert len(mc.predict_set(probs[0], "UNKNOWN")) >= 1

    for col in MODEL_FEATURES:
        assert "closure" not in col and "cause" not in col and "repair_note" not in col


@pytest.mark.slow
def test_t2_full_twelve_scenario_gate() -> None:
    corpus = build_mode_corpus(seeds=(42, 43, 99))
    bundle = train_diagnosis_model(corpus, seed=42, test_seed=99, alpha=0.09)
    assert bundle.macro_f1 > bundle.baseline_macro_f1
    assert 0.88 <= bundle.coverage <= 0.92
    assert bundle.mean_set_size <= 3.0
