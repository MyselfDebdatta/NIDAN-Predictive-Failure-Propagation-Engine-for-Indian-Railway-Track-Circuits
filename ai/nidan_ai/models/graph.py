"""T3 short-horizon risk and common-cause graph.

A heterogeneous graph is built per division: electrical adjacency, shared asset (power,
cable, room, network), weather cell and work history. The shipped POC path is a deterministic
CPU graph-propagation model; an optional torch GraphSAGE is provided behind the ``graph``
extra and never required. The no-graph ablation is a hard gate: if the graph does not beat it
with a station-level bootstrap CI excluding zero, the per-circuit model ships and the
negative result is reported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from nidan_ai.bench.generator import AssetSpec, BenchStream, generate
from nidan_ai.bench.scenarios import SCENARIO_NAMES
from nidan_ai.data.canonical import from_bench
from nidan_ai.data.features import FeatureVector, build_features, context_from_asset
from nidan_ai.eval.metrics import (
    average_precision,
    brier_score,
    expected_calibration_error,
    precision_at_k,
)

EDGE_KINDS = ("weather_cell", "shared_asset", "route_dependency", "work_history")


@dataclass(frozen=True, slots=True)
class GraphEdge:
    kind: str
    source: str
    target: str
    id: str
    note: str = ""


@dataclass(slots=True)
class AssetGraph:
    """Division graph over assets and shared infrastructure (read-only topology)."""

    assets: dict[str, AssetSpec]
    edges: list[GraphEdge] = field(default_factory=list)

    @classmethod
    def from_assets(
        cls,
        assets: list[AssetSpec],
        *,
        work_history: list[tuple[str, str, str]] | None = None,
    ) -> AssetGraph:
        graph = cls(assets={asset.asset_id: asset for asset in assets})
        ids = sorted(graph.assets)
        for i, source in enumerate(ids):
            for target in ids[i + 1 :]:
                left, right = graph.assets[source], graph.assets[target]
                if left.weather_cell == right.weather_cell:
                    graph.edges.append(
                        GraphEdge(
                            "weather_cell",
                            source,
                            target,
                            left.weather_cell,
                            "same weather cell",
                        )
                    )
                if left.supply_id == right.supply_id:
                    graph.edges.append(
                        GraphEdge("shared_asset", source, target, left.supply_id, "shared supply")
                    )
                if left.cable_id == right.cable_id:
                    graph.edges.append(
                        GraphEdge("shared_asset", source, target, left.cable_id, "shared cable")
                    )
                if left.relay_room == right.relay_room:
                    graph.edges.append(
                        GraphEdge(
                            "shared_asset", source, target, left.relay_room, "shared relay room"
                        )
                    )
                if left.route == right.route:
                    graph.edges.append(
                        GraphEdge(
                            "route_dependency",
                            source,
                            target,
                            f"{left.station}:{left.route}",
                            "same route (read-only topology)",
                        )
                    )
        for source, target, job_id in work_history or []:
            if source in graph.assets and target in graph.assets and source != target:
                graph.edges.append(
                    GraphEdge("work_history", source, target, job_id, "shared work history")
                )
        return graph

    def neighbours(self, asset_id: str, kind: str | None = None) -> list[str]:
        found: set[str] = set()
        for edge in self.edges:
            if kind is not None and edge.kind != kind:
                continue
            if edge.source == asset_id:
                found.add(edge.target)
            elif edge.target == asset_id:
                found.add(edge.source)
        return sorted(found)

    def shared_ids(self, asset_id: str, other: str) -> list[GraphEdge]:
        return [edge for edge in self.edges if {edge.source, edge.target} == {asset_id, other}]


@dataclass(slots=True)
class RiskSample:
    """One snapshot sample for T3 training/evaluation."""

    vector: FeatureVector
    labels: dict[str, int]
    stream_key: str
    snapshot_day: int
    station: str
    division: str


@dataclass(slots=True)
class RiskCorpus:
    samples: list[RiskSample] = field(default_factory=list)
    graphs: dict[str, AssetGraph] = field(default_factory=dict)
    streams: dict[str, BenchStream] = field(default_factory=dict)

    def arrays(self) -> tuple[list[RiskSample], dict[str, np.ndarray]]:
        labels = {
            horizon: np.array([sample.labels[horizon] for sample in self.samples], dtype=int)
            for horizon in ("h24", "h72", "h7d")
        }
        return self.samples, labels


def _snapshot_days(stream: BenchStream, asset: AssetSpec) -> list[int]:
    event = stream.event_for(asset.asset_id)
    if event is None:
        candidates = [10, 20, 30, 40]
    else:
        candidates = [event.event_day - offset for offset in (7, 5, 3, 1)]
    days = stream.scenario_def.days
    return sorted({max(2, min(days - 1, day)) for day in candidates})


def build_risk_corpus(
    *,
    seeds: tuple[int, ...] = (42, 43),
    scenarios: tuple[str, ...] = SCENARIO_NAMES,
) -> RiskCorpus:
    """Build a multi-stream risk corpus with shared-cause graph structure."""
    corpus = RiskCorpus()
    for scenario_name in scenarios:
        for seed in seeds:
            stream = generate(scenario_name, seed=seed)
            stream_key = f"{scenario_name}:{seed}"
            corpus.streams[stream_key] = stream
            corpus.graphs[stream_key] = AssetGraph.from_assets(stream.assets)
            dataset = from_bench(stream, as_of=stream.timestamps[-1])
            for asset in stream.assets:
                event = stream.event_for(asset.asset_id)
                event_day = event.event_day if event is not None else None
                context = context_from_asset(asset)
                for day in _snapshot_days(stream, asset):
                    vector = build_features(
                        dataset.assets[asset.asset_id],
                        context,
                        stream.timestamps[day * 24],
                        clock_offset_minutes=stream.clock_offsets_minutes.get(asset.asset_id, 0),
                    )
                    labels: dict[str, int] = {}
                    for horizon, horizon_days in (("h24", 1), ("h72", 3), ("h7d", 7)):
                        if event_day is None:
                            labels[horizon] = 0
                        else:
                            delta = event_day - day
                            labels[horizon] = int(0 < delta <= horizon_days)
                    corpus.samples.append(
                        RiskSample(
                            vector=vector,
                            labels=labels,
                            stream_key=stream_key,
                            snapshot_day=day,
                            station=asset.station,
                            division=asset.division,
                        )
                    )
    return corpus


def _standardize(train: np.ndarray, other: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    center = np.mean(train, axis=0)
    scale = np.std(train, axis=0)
    scale = np.where(scale > 1e-9, scale, 1.0)
    return (train - center) / scale, (other - center) / scale


@dataclass(slots=True)
class GraphRiskModel:
    """CPU graph-propagation model with an explicit no-graph ablation."""

    base_model: Any
    graph_model: Any
    center: np.ndarray
    scale: np.ndarray
    feature_names: tuple[str, ...]
    graph_feature_names: tuple[str, ...]
    metrics: dict[str, float] = field(default_factory=dict)
    bootstrap_ci: dict[str, tuple[float, float]] = field(default_factory=dict)
    used_torch: bool = False
    ship_graph: bool = True
    negative_result: str | None = None

    @classmethod
    def fit(
        cls,
        samples: list[RiskSample],
        graphs: dict[str, AssetGraph],
        *,
        horizon: str = "h7d",
        seed: int = 42,
    ) -> GraphRiskModel:
        from sklearn.linear_model import LogisticRegression

        if not samples:
            raise ValueError("Risk corpus is empty")
        x = np.vstack([sample.vector.array() for sample in samples])
        y = np.array([sample.labels[horizon] for sample in samples], dtype=int)
        center = np.mean(x, axis=0)
        scale = np.std(x, axis=0)
        scale = np.where(scale > 1e-9, scale, 1.0)
        z = (x - center) / scale
        base_model = LogisticRegression(C=0.8, max_iter=400, solver="lbfgs", random_state=seed).fit(
            z, y
        )
        base_logit = _logit(base_model.predict_proba(z)[:, 1])
        graph_x = _graph_features(samples, graphs, base_logit)
        graph_model = LogisticRegression(
            C=0.8, max_iter=400, solver="lbfgs", random_state=seed
        ).fit(graph_x, y)
        return cls(
            base_model=base_model,
            graph_model=graph_model,
            center=center,
            scale=scale,
            feature_names=tuple(sorted(samples[0].vector.values)),
            graph_feature_names=tuple(
                [
                    "own_logit",
                    "own_margin",
                    "own_slope_7d",
                    "own_harmonic",
                    "neigh_logit_weather",
                    "neigh_logit_shared",
                    "neigh_logit_route",
                    "neigh_margin_shared",
                    "neigh_slope_shared",
                    "neigh_harmonic_shared",
                    "neigh_count",
                ]
            ),
        )

    def own_logit(self, vector: FeatureVector) -> float:
        row = (vector.array() - self.center) / self.scale
        return float(_logit(self.base_model.predict_proba(row.reshape(1, -1))[:, 1])[0])

    def own_probability(self, vector: FeatureVector) -> float:
        row = (vector.array() - self.center) / self.scale
        return float(np.clip(self.base_model.predict_proba(row.reshape(1, -1))[0, 1], 0.0, 1.0))

    def predict(
        self, vector: FeatureVector, neighbour_logits: dict[str, list[float]] | None = None
    ) -> float:
        own = self.own_logit(vector)
        nl = neighbour_logits or {}
        features = np.array(
            [
                own,
                vector.get("margin_ratio"),
                vector.get("margin_slope_7d"),
                vector.get("harmonic_mv_24h"),
                float(np.mean(nl.get("weather_cell") or [own])),
                float(np.mean(nl.get("shared_asset") or [own])),
                float(np.mean(nl.get("route_dependency") or [own])),
                float(np.mean(nl.get("shared_asset_margin") or [vector.get("margin_ratio")])),
                float(np.mean(nl.get("shared_asset_slope") or [vector.get("margin_slope_7d")])),
                float(np.mean(nl.get("shared_asset_harmonic") or [vector.get("harmonic_mv_24h")])),
                float(sum(len(values) for values in nl.values())),
            ],
            dtype=float,
        )
        probability = self.graph_model.predict_proba(features.reshape(1, -1))[0, 1]
        return float(np.clip(probability, 0.0, 1.0))

    def predict_honest(
        self, vector: FeatureVector, neighbour_logits: dict[str, list[float]] | None = None
    ) -> float:
        """Use graph model only when the no-graph ablation gate passed; else per-circuit."""
        if not self.ship_graph:
            return self.own_probability(vector)
        return self.predict(vector, neighbour_logits)


def _logit(probability: np.ndarray) -> np.ndarray:
    probability = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(probability / (1.0 - probability))


def _graph_features(
    samples: list[RiskSample],
    graphs: dict[str, AssetGraph],
    base_logit: np.ndarray,
) -> np.ndarray:
    lookup: dict[tuple[str, int], list[int]] = {}
    for index, sample in enumerate(samples):
        lookup.setdefault((sample.stream_key, sample.snapshot_day), []).append(index)
    rows: list[list[float]] = []
    for index, sample in enumerate(samples):
        graph = graphs[sample.stream_key]
        group = [
            other for other in lookup[(sample.stream_key, sample.snapshot_day)] if other != index
        ]
        own = float(base_logit[index])

        def mean_for(
            kind: str,
            attribute: str | None = None,
            default: float = 0.0,
            *,
            _group: list[int] = group,
            _graph: AssetGraph = graph,
            _sample: RiskSample = sample,
        ) -> float:
            values: list[float] = []
            for other_index in _group:
                other = samples[other_index]
                if other.vector.asset_id in _graph.neighbours(_sample.vector.asset_id, kind):
                    values.append(
                        float(other.vector.get(attribute))
                        if attribute
                        else float(base_logit[other_index])
                    )
            return float(np.mean(values)) if values else default

        rows.append(
            [
                own,
                sample.vector.get("margin_ratio"),
                sample.vector.get("margin_slope_7d"),
                sample.vector.get("harmonic_mv_24h"),
                mean_for("weather_cell"),
                mean_for("shared_asset"),
                mean_for("route_dependency"),
                mean_for("shared_asset", "margin_ratio"),
                mean_for("shared_asset", "margin_slope_7d"),
                mean_for("shared_asset", "harmonic_mv_24h"),
                float(len(group)),
            ]
        )
    return np.asarray(rows, dtype=float)


def hawkes_baseline_scores(
    samples: list[RiskSample],
    model: GraphRiskModel,
    *,
    decay_days: float = 3.0,
    excitation: float = 0.25,
) -> np.ndarray:
    """Self-exciting Hawkes baseline: own probability + exponentially decayed station activity."""
    by_stream: dict[str, list[RiskSample]] = {}
    for sample in samples:
        by_stream.setdefault(sample.stream_key, []).append(sample)
    scores: list[float] = []
    for sample in samples:
        own = model.own_probability(sample.vector)
        trigger = 0.0
        peers = by_stream.get(sample.stream_key, [])
        for other in peers:
            if other.vector.asset_id == sample.vector.asset_id:
                continue
            dt = sample.snapshot_day - other.snapshot_day
            if 0 <= dt <= 14:
                other_prob = model.own_probability(other.vector)
                if other_prob > 0.35:
                    trigger += float(np.exp(-dt / max(decay_days, 0.5)) * other_prob)
        intensity = own + excitation * min(1.0, trigger / max(1, len(peers)))
        scores.append(float(np.clip(intensity, 0.0, 1.0)))
    return np.asarray(scores, dtype=float)


def bayesian_network_scores(
    samples: list[RiskSample],
    graphs: dict[str, AssetGraph],
    model: GraphRiskModel,
) -> np.ndarray:
    """Factorized noisy-OR Bayesian network cause-attribution baseline."""
    lookup: dict[tuple[str, int], list[RiskSample]] = {}
    for sample in samples:
        lookup.setdefault((sample.stream_key, sample.snapshot_day), []).append(sample)
    scores: list[float] = []
    for sample in samples:
        p_own = model.own_probability(sample.vector)
        graph = graphs[sample.stream_key]
        peers = [
            other
            for other in lookup.get((sample.stream_key, sample.snapshot_day), [])
            if other.vector.asset_id != sample.vector.asset_id
        ]
        shared_alarm = [
            model.own_probability(other.vector)
            for other in peers
            if graph.shared_ids(sample.vector.asset_id, other.vector.asset_id)
        ]
        p_common = 0.35 * float(np.mean(shared_alarm)) if shared_alarm else 0.0
        noisy_or = 1.0 - (1.0 - p_own) * (1.0 - p_common)
        scores.append(float(np.clip(noisy_or, 0.0, 1.0)))
    return np.asarray(scores, dtype=float)


def evaluate_graph_gate(
    corpus: RiskCorpus,
    *,
    horizon: str = "h7d",
    seed: int = 42,
    bootstrap: int = 800,
    top_k: int = 10,
) -> tuple[GraphRiskModel, dict[str, float], dict[str, tuple[float, float]]]:
    """Leave-one-station-out evaluation with baselines and station-level bootstrap CIs."""
    stations = sorted({sample.station for sample in corpus.samples})
    if len(stations) < 3:
        raise ValueError("At least three stations are required for the graph gate")
    differences_ap: list[float] = []
    differences_pk: list[float] = []
    per_station: dict[str, dict[str, float]] = {}
    for station in stations:
        train = [sample for sample in corpus.samples if sample.station != station]
        test = [sample for sample in corpus.samples if sample.station == station]
        if not train or not test:
            continue
        model = GraphRiskModel.fit(train, corpus.graphs, horizon=horizon, seed=seed)
        y = np.array([sample.labels[horizon] for sample in test], dtype=int)
        base_probs = np.array([model.own_probability(sample.vector) for sample in test])
        hawkes_probs = hawkes_baseline_scores(test, model)
        bayes_probs = bayesian_network_scores(test, corpus.graphs, model)
        # Graph scores use neighbour logits from the same held-out station.
        graph_scores = []
        for sample in test:
            peers = [
                other
                for other in test
                if other.stream_key == sample.stream_key
                and other.snapshot_day == sample.snapshot_day
                and other.vector.asset_id != sample.vector.asset_id
            ]
            graph = corpus.graphs[sample.stream_key]
            neighbour_logits: dict[str, list[float]] = {
                "weather_cell": [],
                "shared_asset": [],
                "route_dependency": [],
                "shared_asset_margin": [],
                "shared_asset_slope": [],
                "shared_asset_harmonic": [],
            }
            for other in peers:
                kinds = {
                    edge.kind
                    for edge in graph.shared_ids(sample.vector.asset_id, other.vector.asset_id)
                }
                other_logit = model.own_logit(other.vector)
                for kind in kinds:
                    neighbour_logits.setdefault(kind, []).append(other_logit)
                if "shared_asset" in kinds:
                    neighbour_logits["shared_asset_margin"].append(other.vector.get("margin_ratio"))
                    neighbour_logits["shared_asset_slope"].append(
                        other.vector.get("margin_slope_7d")
                    )
                    neighbour_logits["shared_asset_harmonic"].append(
                        other.vector.get("harmonic_mv_24h")
                    )
            graph_scores.append(model.predict(sample.vector, neighbour_logits))
        graph_probs = np.array(graph_scores)
        ap_base = average_precision(base_probs, y)
        ap_hawkes = average_precision(hawkes_probs, y)
        ap_bayes = average_precision(bayes_probs, y)
        ap_graph = average_precision(graph_probs, y)
        pk_base = precision_at_k(base_probs, y, k=top_k)
        pk_hawkes = precision_at_k(hawkes_probs, y, k=top_k)
        pk_bayes = precision_at_k(bayes_probs, y, k=top_k)
        pk_graph = precision_at_k(graph_probs, y, k=top_k)
        differences_ap.append(ap_graph - ap_base)
        differences_pk.append(pk_graph - pk_base)
        per_station[station] = {
            "pr_auc_base": ap_base,
            "pr_auc_hawkes": ap_hawkes,
            "pr_auc_bayes": ap_bayes,
            "pr_auc_graph": ap_graph,
            "precision_at_k_base": pk_base,
            "precision_at_k_hawkes": pk_hawkes,
            "precision_at_k_bayes": pk_bayes,
            "precision_at_k_graph": pk_graph,
            "ece_base": expected_calibration_error(base_probs, y, bins=10),
            "ece_graph": expected_calibration_error(graph_probs, y, bins=10),
            "brier_base": brier_score(base_probs, y),
            "brier_graph": brier_score(graph_probs, y),
            "n": float(len(y)),
            "positives": float(y.sum()),
        }

    # Refit on all data for the shipped model.
    model = GraphRiskModel.fit(corpus.samples, corpus.graphs, horizon=horizon, seed=seed)
    rng = np.random.default_rng(seed)
    ap_diffs = np.array(differences_ap)
    pk_diffs = np.array(differences_pk)
    ap_boot = np.array(
        [np.mean(rng.choice(ap_diffs, size=ap_diffs.size, replace=True)) for _ in range(bootstrap)]
    )
    pk_boot = np.array(
        [np.mean(rng.choice(pk_diffs, size=pk_diffs.size, replace=True)) for _ in range(bootstrap)]
    )
    ci_ap = (float(np.percentile(ap_boot, 2.5)), float(np.percentile(ap_boot, 97.5)))
    ci_pk = (float(np.percentile(pk_boot, 2.5)), float(np.percentile(pk_boot, 97.5)))
    metrics = {
        "pr_auc_base": float(np.mean([item["pr_auc_base"] for item in per_station.values()])),
        "pr_auc_hawkes": float(np.mean([item["pr_auc_hawkes"] for item in per_station.values()])),
        "pr_auc_bayes": float(np.mean([item["pr_auc_bayes"] for item in per_station.values()])),
        "pr_auc_graph": float(np.mean([item["pr_auc_graph"] for item in per_station.values()])),
        "precision_at_k_base": float(
            np.mean([item["precision_at_k_base"] for item in per_station.values()])
        ),
        "precision_at_k_hawkes": float(
            np.mean([item["precision_at_k_hawkes"] for item in per_station.values()])
        ),
        "precision_at_k_bayes": float(
            np.mean([item["precision_at_k_bayes"] for item in per_station.values()])
        ),
        "precision_at_k_graph": float(
            np.mean([item["precision_at_k_graph"] for item in per_station.values()])
        ),
        "ece_base": float(np.mean([item["ece_base"] for item in per_station.values()])),
        "ece_graph": float(np.mean([item["ece_graph"] for item in per_station.values()])),
        "brier_base": float(np.mean([item["brier_base"] for item in per_station.values()])),
        "brier_graph": float(np.mean([item["brier_graph"] for item in per_station.values()])),
        "pr_auc_difference": float(np.mean(ap_diffs)),
        "precision_at_k_difference": float(np.mean(pk_diffs)),
        "top_k": float(top_k),
        "n": float(len(corpus.samples)),
        "positives": float(np.sum([sample.labels[horizon] for sample in corpus.samples])),
        "stations": float(len(per_station)),
    }
    beats_ap = ci_ap[0] > 0.0
    beats_pk = ci_pk[0] > 0.0
    model.ship_graph = bool(beats_ap and beats_pk)
    if not model.ship_graph:
        model.negative_result = (
            f"Graph did not clear both 95% station-bootstrap CI gates vs no-graph "
            f"(PR-AUC diff={metrics['pr_auc_difference']:+.4f} CI={ci_ap}, "
            f"P@{top_k} diff={metrics['precision_at_k_difference']:+.4f} CI={ci_pk}); "
            "shipping per-circuit base model."
        )
    model.metrics = metrics
    model.bootstrap_ci = {
        "pr_auc_difference": ci_ap,
        "precision_at_k_difference": ci_pk,
    }
    return model, metrics, model.bootstrap_ci


@dataclass(slots=True)
class ClusterCandidate:
    """Derived common-cause cluster (never written onto an asset row)."""

    id: str
    title: str
    summary: str
    members: list[str]
    root: str
    posterior: float
    shared_edges: list[dict[str, str]]
    weather_cell: str
    cascade_min_days: int | None = None
    cascade_max_days: int | None = None


def cluster_candidates(
    stream: BenchStream,
    risks: dict[str, float],
    *,
    threshold: float = 0.35,
    window_label: str,
) -> list[ClusterCandidate]:
    """Derive clusters from the graph posterior plus shared edges."""
    from nidan_ai.bench.manifest import stable_id

    graph = AssetGraph.from_assets(stream.assets)
    active = sorted(asset_id for asset_id, risk in risks.items() if risk >= threshold)
    if len(active) < 2:
        return []
    # Connected components over active assets sharing a physical edge.
    remaining = set(active)
    components: list[list[str]] = []
    while remaining:
        start = sorted(remaining)[0]
        stack = [start]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            for neighbour in graph.neighbours(current):
                if neighbour in remaining and neighbour not in component:
                    stack.append(neighbour)
        remaining -= component
        components.append(sorted(component))
    candidates: list[ClusterCandidate] = []
    for component in components:
        if len(component) < 2:
            continue
        mean_risk = float(np.mean([risks[asset_id] for asset_id in component]))
        edge_bonus = min(0.15, 0.03 * len(component))
        posterior = float(np.clip(mean_risk + edge_bonus, 0.0, 1.0))
        if posterior < 0.55:
            continue
        root = max(component, key=lambda asset_id: (risks[asset_id], asset_id))
        shared_edges: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for i, left in enumerate(component):
            for right in component[i + 1 :]:
                for edge in graph.shared_ids(left, right):
                    key = (edge.kind, edge.id)
                    if key in seen:
                        continue
                    seen.add(key)
                    shared_edges.append({"kind": edge.kind, "id": edge.id, "note": edge.note})
        shared_edges.sort(key=lambda item: (item["kind"], item["id"]))
        kind = shared_edges[0]["kind"] if shared_edges else "shared_asset"
        cluster_id = "c-" + stable_id("cluster", sorted(component), root, window_label, 8)
        candidates.append(
            ClusterCandidate(
                id=cluster_id,
                title=f"{kind.replace('_', ' ').title()} cluster",
                summary=(
                    f"{len(component)} circuits share a common-cause signature; "
                    f"root candidate {root} with posterior {posterior:.2f}."
                ),
                members=component,
                root=root,
                posterior=posterior,
                shared_edges=shared_edges[:4],
                weather_cell=stream.by_id(root).weather_cell,
                cascade_min_days=1,
                cascade_max_days=7,
            )
        )
    candidates.sort(key=lambda candidate: candidate.id)
    return candidates


def torch_available() -> bool:
    """Whether the optional heterogeneous GNN extra is installed."""
    try:
        import torch  # noqa: F401

        return True
    except Exception:  # pragma: no cover - optional
        return False


class HeterogeneousGraphSAGE:
    """Optional torch GraphSAGE per edge type.

    The POC metrics in this repository are produced by the deterministic CPU graph-propagation
    fallback. This class is provided for scale-out experiments and is never required in CI.
    """

    def __init__(self, in_dim: int, hidden: int = 32, edge_types: tuple[str, ...] = EDGE_KINDS):
        try:
            import torch
            from torch import nn
        except ImportError as exc:  # pragma: no cover - optional
            raise RuntimeError("Install nidan-ai[graph] to use HeterogeneousGraphSAGE") from exc
        self.torch = torch
        self.edge_types = edge_types
        self.self_linear = nn.Linear(in_dim, hidden)
        self.edge_linears = nn.ModuleDict({kind: nn.Linear(in_dim, hidden) for kind in edge_types})
        self.output = nn.Linear(hidden, 1)

    def forward(self, x, adjacency: dict[str, Any]):
        """One message-passing step per edge type."""
        torch = self.torch
        message = self.self_linear(x)
        for kind, neighbours in adjacency.items():
            if kind not in self.edge_linears:
                continue
            aggregated = neighbours @ x
            message = message + self.edge_linears[kind](aggregated)
        return torch.sigmoid(self.output(torch.relu(message))).squeeze(-1)
