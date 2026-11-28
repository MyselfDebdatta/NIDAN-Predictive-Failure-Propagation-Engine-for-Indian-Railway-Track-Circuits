"""Phase A4 tests: heterogeneous graph, baselines, bootstrap CI gate, and clustering."""

from __future__ import annotations

from nidan_ai.bench.generator import generate
from nidan_ai.models.graph import (
    AssetGraph,
    bayesian_network_scores,
    build_risk_corpus,
    cluster_candidates,
    evaluate_graph_gate,
    hawkes_baseline_scores,
)


def test_asset_graph_builds_all_four_edge_kinds() -> None:
    stream = generate("lightning-cluster", seed=42)
    ids = stream.asset_ids
    graph = AssetGraph.from_assets(
        stream.assets,
        work_history=[(ids[0], ids[1], "WO-101")],
    )
    kinds = {edge.kind for edge in graph.edges}
    assert {"weather_cell", "shared_asset", "route_dependency", "work_history"}.issubset(kinds)
    assert ids[1] in graph.neighbours(ids[0], "work_history")


def test_lightning_cluster_is_deterministic_and_does_not_mutate_assets() -> None:
    stream = generate("lightning-cluster", seed=42)
    risks = {asset.asset_id: (0.78 if asset.faulted else 0.12) for asset in stream.assets}
    first = cluster_candidates(stream, risks, window_label="2026-07-10T00:00Z")
    second = cluster_candidates(stream, risks, window_label="2026-07-10T00:00Z")

    assert len(first) >= 1
    assert [c.id for c in first] == [c.id for c in second]
    assert [c.members for c in first] == [c.members for c in second]
    assert all(len(c.members) >= 2 for c in first)
    assert all(c.root in c.members for c in first)
    assert all(not hasattr(asset, "cluster_id") for asset in stream.assets)


def test_single_member_cluster_is_suppressed() -> None:
    stream = generate("lightning-cluster", seed=42)
    risks = {asset.asset_id: 0.05 for asset in stream.assets}
    risks[stream.asset_ids[0]] = 0.90
    assert cluster_candidates(stream, risks, window_label="2026-07-10T00:00Z") == []


def test_graph_gate_computes_baselines_and_enforces_honest_ship_rule() -> None:
    corpus = build_risk_corpus(
        seeds=(42, 43),
        scenarios=("monsoon-60d", "lightning-cluster", "supply-sag", "cable-ingress"),
    )
    model, metrics, ci = evaluate_graph_gate(
        corpus, horizon="h7d", seed=42, bootstrap=200, top_k=10
    )

    for key in (
        "pr_auc_base",
        "pr_auc_hawkes",
        "pr_auc_bayes",
        "pr_auc_graph",
        "precision_at_k_base",
        "precision_at_k_graph",
        "ece_base",
        "ece_graph",
        "brier_base",
        "brier_graph",
    ):
        assert key in metrics

    assert "pr_auc_difference" in ci
    assert "precision_at_k_difference" in ci

    # Verify standalone baseline helpers produce valid [0, 1] probabilities
    hawkes = hawkes_baseline_scores(corpus.samples[:20], model)
    bayes = bayesian_network_scores(corpus.samples[:20], corpus.graphs, model)
    assert hawkes.shape == (20,)
    assert bayes.shape == (20,)
    assert ((hawkes >= 0.0) & (hawkes <= 1.0)).all()
    assert ((bayes >= 0.0) & (bayes <= 1.0)).all()

    # Honest shipping rule: if CI excludes zero on both, ship_graph=True; otherwise per-circuit
    sample = corpus.samples[0]
    if ci["pr_auc_difference"][0] > 0.0 and ci["precision_at_k_difference"][0] > 0.0:
        assert model.ship_graph is True
    else:
        assert model.ship_graph is False
        assert model.negative_result is not None
        assert model.predict_honest(sample.vector) == model.own_probability(sample.vector)
