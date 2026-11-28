"""Phase A6 tests: T5 dual detection, three-lens explainer, precedents, and policy boundaries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from nidan_ai.bench.generator import generate
from nidan_ai.data.canonical import from_bench
from nidan_ai.data.features import build_features, context_from_asset
from nidan_ai.explain.narrative import agreement, model_narrative, physics_narrative
from nidan_ai.explain.precedents import PrecedentIndex
from nidan_ai.models.dual_detection import assess_dual_detection
from nidan_ai.policy.levels import PersistenceTracker, assign_ranks, decide_level, make_decision


def test_t5_detects_masked_decay_and_turns_off_without_axle_counter() -> None:
    stream = generate("masked-decay", seed=42)
    dataset = from_bench(stream, as_of=stream.timestamps[-1])
    faulted = next(a for a in stream.assets if a.faulted)
    ctx = context_from_asset(faulted)
    fv = build_features(dataset.assets[faulted.asset_id], ctx, stream.timestamps[50 * 24])

    res_on = assess_dual_detection(fv, axle_available=True)
    assert res_on.enabled is True
    assert res_on.masked is True
    assert res_on.score >= 0.45

    res_off = assess_dual_detection(fv, axle_available=False)
    assert res_off.enabled is False
    assert res_off.masked is False
    assert res_off.score == 0.0


def test_three_lens_narrative_agreement_and_precedent_guardrails() -> None:
    stream = generate("monsoon-60d", seed=42, days=15)
    dataset = from_bench(stream, as_of=stream.timestamps[-1])
    asset = stream.assets[0]
    fv = build_features(
        dataset.assets[asset.asset_id], context_from_asset(asset), stream.timestamps[-1]
    )

    for mode in ("F1", "F3", "F5", "F6", "F12", "F9"):
        phys = physics_narrative(fv, fv.twin, mode=mode)
        assert "effective ballast conductance" in phys.headline.lower()
        assert 2 <= len(phys.state) <= 4
        assert len(phys.falsifier) > 20

    assert (
        agreement(
            physics_driver="gb_ratio",
            shap_top=[{"feature": "margin_ratio", "label": "Relay margin", "value": 0.25}],
            mode_set=["F1"],
            trust_score=0.95,
        )
        == "high"
    )
    assert (
        agreement(
            physics_driver="gb_ratio",
            shap_top=[{"feature": "margin_ratio", "label": "Relay margin", "value": 0.25}],
            mode_set=["F1", "F6"],
            trust_score=0.95,
        )
        == "medium"
    )
    assert (
        agreement(
            physics_driver="gb_ratio",
            shap_top=[{"feature": "margin_ratio", "label": "Relay margin", "value": 0.25}],
            mode_set=["F1"],
            trust_score=0.45,
        )
        == "low"
    )

    m_exp = model_narrative(
        shap_top=[{"feature": "gb_ratio", "label": "Ballast conductance", "value": 0.2}],
        mode_set=["F1"],
        coverage=0.90,
        held_out_n=100,
        agreement_level="high",
    )
    assert m_exp["modeSetCoverage"] == 0.90
    assert "100" in str(m_exp["calibrationNote"])

    # Events without feature vectors must not fabricate similarity=1.0; empty list is valid.
    as_of = stream.timestamps[-1]
    events_no_fv = [
        {
            "smmsId": "SMMS-1",
            "assetId": asset.asset_id,
            "confirmedMode": "F1",
            "mode": "F1",
            "eventTime": (as_of - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "outcome": "Confirmed",
            "station": asset.station,
        }
    ]
    assert PrecedentIndex(events_no_fv).retrieve(fv, as_of=as_of) == []

    events_with_fv = [
        {
            **events_no_fv[0],
            "featureVector": {
                "margin_ratio": fv.get("margin_ratio"),
                "gb_ratio": fv.get("gb_ratio"),
                "drop_p95_ms": fv.get("drop_p95_ms"),
                "rain_72h": fv.get("rain_72h"),
                "age_ratio": fv.get("age_ratio"),
            },
        }
    ]
    idx = PrecedentIndex(events_with_fv)
    hits1 = idx.retrieve(fv, as_of=as_of, cache_key="hash-1")
    hits2 = idx.retrieve(fv, as_of=as_of, cache_key="hash-1")
    assert len(hits1) == 1
    assert hits1[0].days_ago == 10
    assert hits1 == hits2


def test_policy_exact_threshold_ties_and_ranking_determinism() -> None:
    # Exact 0.50 on h24 is NOT critical (strict > 0.50);
    # exact 0.30 on h72 is NOT warning (strict > 0.30).
    lvl_50, hor_50, risk_50 = decide_level(h24=0.50, h72=0.50, h7d=0.60, cluster_root=False)
    assert (lvl_50, hor_50, risk_50) == ("warning", "h72", 0.50)

    lvl_30, hor_30, risk_30 = decide_level(h24=0.10, h72=0.30, h7d=0.45, cluster_root=False)
    assert (lvl_30, hor_30, risk_30) == ("watch", "h7d", 0.45)

    lvl_root, hor_root, _ = decide_level(h24=0.10, h72=0.15, h7d=0.20, cluster_root=True)
    assert (lvl_root, hor_root) == ("critical", "h24")

    d1 = make_decision(
        asset_id="ADRA/TC/12T",
        h24=0.2,
        h72=0.35,
        h7d=0.55,
        p10_days=10,
        persistence=2,
        trust_score=0.9,
        traffic_per_day=90,
        route="Up Main",
    )
    d2 = make_decision(
        asset_id="ADRA/TC/14T",
        h24=0.1,
        h72=0.2,
        h7d=0.35,
        p10_days=20,
        persistence=1,
        trust_score=0.9,
        traffic_per_day=30,
        route="Loop",
    )
    ranked = assign_ranks([d2, d1])
    assert [d.asset_id for d in ranked] == ["ADRA/TC/12T", "ADRA/TC/14T"]
    assert [d.policy_rank for d in ranked] == [1, 2]

    tracker = PersistenceTracker(threshold=0.20)
    assert tracker.update("A", 0.15) == 0
    assert tracker.update("A", 0.25) == 1
    assert tracker.update("A", 0.30) == 2
    assert tracker.persistence("A") == 2
    assert datetime(2026, 7, 14, tzinfo=UTC).tzinfo == UTC
