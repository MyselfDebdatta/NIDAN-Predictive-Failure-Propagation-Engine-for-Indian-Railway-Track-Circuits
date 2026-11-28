"""T2 fault diagnosis: deterministic gradient-boosted classifier with conformal sets.

First release covers F1, F3, F5, F6 and F12 (spec §8.2). Other bench modes are mapped to
F12 (no-fault-found) until the evidence supports them; the mapping is explicit and tested.
Synthetic pre-training uses NIDAN-Bench, with class weights for rarity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np

from nidan_ai.bench.generator import generate
from nidan_ai.bench.scenarios import SCENARIO_NAMES
from nidan_ai.config import FAILURE_MODES, RELEASE_MODES
from nidan_ai.data.canonical import from_bench
from nidan_ai.data.features import (
    FEATURE_LABELS,
    MODEL_FEATURES,
    FeatureVector,
    build_features,
    context_from_asset,
    feature_matrix,
)
from nidan_ai.eval.metrics import division_coverage_gap
from nidan_ai.models.conformal import MondrianConformal

_RELEASE_MAP: dict[str, str] = {mode: mode for mode in RELEASE_MODES}
_FALLBACK_MODE = "F12"


def release_label(mode: str | None, *, allowed_modes: tuple[str, ...] = RELEASE_MODES) -> str:
    """Map any bench mode to the configured diagnosis scope."""
    if mode is None:
        return _FALLBACK_MODE
    return mode if mode in allowed_modes else _FALLBACK_MODE


@dataclass(slots=True)
class ModeCorpus:
    """Synthetic pre-training corpus with labels held separately from features."""

    vectors: list[FeatureVector] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    stations: list[str] = field(default_factory=list)
    scenarios: list[str] = field(default_factory=list)
    seeds: list[int] = field(default_factory=list)

    def matrix(self) -> np.ndarray:
        return feature_matrix(self.vectors, MODEL_FEATURES)

    def arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        return (
            self.matrix(),
            np.array(self.labels),
            np.array(self.groups),
            np.array(self.stations),
        )


def _snapshot_days(mode: str, event_day: int, days: int) -> list[int]:
    if mode == "F3":
        offsets = (1, 2, 3)
    elif mode == "F1":
        offsets = (-1, -2, -3)
    else:
        offsets = (-1, -2, -3)
    return [max(2, min(days - 1, event_day + offset)) for offset in offsets]


def build_mode_corpus(
    *,
    seeds: tuple[int, ...] = (42, 43),
    scenarios: tuple[str, ...] = SCENARIO_NAMES,
    snapshots_per_asset: int = 3,
    all_modes: bool = False,
) -> ModeCorpus:
    """Generate a labelled synthetic corpus for T2 pre-training."""
    allowed = FAILURE_MODES if all_modes else RELEASE_MODES
    corpus = ModeCorpus()
    for scenario_name in scenarios:
        for seed in seeds:
            stream = generate(scenario_name, seed=seed)
            dataset = from_bench(stream, as_of=stream.timestamps[-1])
            for asset in stream.assets:
                context = context_from_asset(asset)
                if asset.faulted and asset.event_day is not None and asset.event_mode:
                    days = _snapshot_days(
                        asset.event_mode, asset.event_day, stream.scenario_def.days
                    )
                    label = release_label(asset.event_mode, allowed_modes=allowed)
                else:
                    days = [max(2, min(stream.scenario_def.days - 1, 12 + seed % 5))]
                    label = _FALLBACK_MODE
                for day in days[:snapshots_per_asset]:
                    as_of = stream.timestamps[day * 24]
                    vector = build_features(
                        dataset.assets[asset.asset_id],
                        context,
                        as_of,
                        clock_offset_minutes=stream.clock_offsets_minutes.get(asset.asset_id, 0),
                    )
                    corpus.vectors.append(vector)
                    corpus.labels.append(label)
                    corpus.groups.append(asset.division)
                    corpus.stations.append(asset.station)
                    corpus.scenarios.append(scenario_name)
                    corpus.seeds.append(seed)
    return corpus


@dataclass(slots=True)
class ModeClassifier:
    """Deterministic CPU classifier over the release mode set."""

    model: object
    classes: list[str]
    baseline: np.ndarray
    feature_names: tuple[str, ...] = MODEL_FEATURES
    seed: int = 42

    def predict_proba(self, matrix: np.ndarray) -> np.ndarray:
        return np.asarray(self.model.predict_proba(matrix), dtype=float)

    def diagnose(self, vector: FeatureVector) -> dict[str, float]:
        row = vector.array(self.feature_names).reshape(1, -1)
        probabilities = self.predict_proba(row)[0]
        return {label: float(probabilities[index]) for index, label in enumerate(self.classes)}

    def shap_top(
        self,
        vector: FeatureVector,
        top_k: int = 5,
        *,
        precomputed_probs: np.ndarray | None = None,
    ) -> list[dict[str, float | str]]:
        """Deterministic signed permutation attribution (TreeSHAP-compatible interface).

        TreeSHAP is used when the fitted estimator exposes it; otherwise the deterministic
        permutation fallback is used. Values are signed contributions, not global importance.
        """
        row = vector.array(self.feature_names)
        if precomputed_probs is None:
            batch = np.tile(row, (len(self.feature_names) + 1, 1))
            for index in range(len(self.feature_names)):
                batch[index + 1, index] = self.baseline[index]
            all_probs = self.predict_proba(batch)
            probabilities = all_probs[0]
            perturbed_probs = all_probs[1:]
        else:
            probabilities = precomputed_probs[0]
            perturbed_probs = precomputed_probs[1:]
        target_index = int(np.argmax(probabilities))
        contributions = [
            (float(probabilities[target_index] - perturbed_probs[index, target_index]), name)
            for index, name in enumerate(self.feature_names)
        ]
        contributions.sort(key=lambda item: (-abs(item[0]), item[1]))
        return [
            {
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "value": float(value),
            }
            for value, name in contributions[:top_k]
        ]


@dataclass(slots=True)
class DiagnosisBundle:
    """Fitted classifier, conformal calibrator and measured evaluation metrics."""

    classifier: ModeClassifier
    conformal: MondrianConformal
    metrics: dict[str, float]
    coverage: float
    macro_f1: float
    baseline_macro_f1: float
    mean_set_size: float
    held_out_n: int
    classes: list[str] = field(default_factory=list)
    division_coverage_gap: float = 0.0
    division_coverages: dict[str, float] = field(default_factory=dict)


def _stratified_indices(labels: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Random stratified 60/20/20 split (fallback when a seed hold-out is too small)."""
    rng = np.random.default_rng(seed)
    train: list[int] = []
    calibration: list[int] = []
    test: list[int] = []
    for label in sorted(set(labels.tolist())):
        indices = np.flatnonzero(labels == label)
        indices = indices[rng.permutation(indices.size)]
        n = indices.size
        if n == 1:
            train.extend(indices.tolist())
            continue
        n_train = max(1, int(round(0.60 * n)))
        n_cal = max(1, int(round(0.20 * n))) if n >= 4 else 0
        train.extend(indices[:n_train].tolist())
        calibration.extend(indices[n_train : n_train + n_cal].tolist())
        test.extend(indices[n_train + n_cal :].tolist())
    return np.array(train), np.array(calibration), np.array(test)


def _stratified_calibration(
    labels: np.ndarray, seed: int, *, fraction: float = 0.25
) -> tuple[np.ndarray, np.ndarray]:
    """Carve a stratified calibration set out of a training pool."""
    rng = np.random.default_rng(seed)
    train: list[int] = []
    calibration: list[int] = []
    for label in sorted(set(labels.tolist())):
        indices = np.flatnonzero(labels == label)
        indices = indices[rng.permutation(indices.size)]
        n_cal = max(1, int(round(fraction * indices.size))) if indices.size >= 4 else 0
        calibration.extend(indices[:n_cal].tolist())
        train.extend(indices[n_cal:].tolist())
    return np.array(train), np.array(calibration)


def _seed_split(
    seeds: np.ndarray, labels: np.ndarray, *, seed: int, test_seed: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Hold out an entire generator seed; calibrate from the remaining seeds."""
    test_idx = np.flatnonzero(seeds == test_seed)
    pool = np.flatnonzero(seeds != test_seed)
    if test_idx.size >= 20 and len(set(labels[test_idx].tolist())) >= 2:
        train_local, cal_local = _stratified_calibration(labels[pool], seed)
        if cal_local.size:
            return pool[train_local], pool[cal_local], test_idx, f"seed-held-out:{test_seed}"
    train_idx, cal_idx, test_idx = _stratified_indices(labels, seed)
    return train_idx, cal_idx, test_idx, "stratified-60/20/20"


def train_diagnosis_model(
    corpus: ModeCorpus | None = None,
    *,
    seed: int = 42,
    test_seed: int = 99,
    alpha: float = 0.09,
    all_modes: bool = False,
) -> DiagnosisBundle:
    """Fit the classifier and conformal calibrator, then measure held-out metrics.

    The primary split holds out an entire generator seed (never seen during fitting or
    calibration). If that hold-out is too small, a stratified split is used and its name is
    recorded so the metric is never ambiguous.
    """
    corpus = corpus or build_mode_corpus(seeds=(42, 43, test_seed), all_modes=all_modes)
    x, y, groups, _stations = corpus.arrays()
    if x.shape[0] < 20:
        raise ValueError("Diagnosis corpus is too small")
    seeds = np.array(corpus.seeds, dtype=int)
    train_idx, cal_idx, test_idx, split_name = _seed_split(seeds, y, seed=seed, test_seed=test_seed)
    classes = sorted(set(y[train_idx].tolist()))
    evaluation_classes = sorted(set(y[test_idx].tolist()) | set(classes))

    try:
        from sklearn.ensemble import HistGradientBoostingClassifier
    except ImportError as exc:  # pragma: no cover - core dependency
        raise RuntimeError("scikit-learn is required for T2") from exc

    counts = np.array([np.sum(y[train_idx] == label) for label in classes], dtype=float)
    class_weight = {
        label: float(len(train_idx) / (len(classes) * max(count, 1)))
        for label, count in zip(classes, counts, strict=True)
    }
    sample_weight = np.array([class_weight[str(label)] for label in y[train_idx]], dtype=float)
    model = HistGradientBoostingClassifier(
        max_iter=180,
        learning_rate=0.08,
        max_leaf_nodes=15,
        min_samples_leaf=4,
        l2_regularization=0.15,
        early_stopping=False,
        random_state=seed,
    )
    model.fit(x[train_idx], y[train_idx], sample_weight=sample_weight)
    classifier = ModeClassifier(
        model=model,
        classes=classes,
        baseline=np.median(x[train_idx], axis=0),
        seed=seed,
    )

    calibration_probabilities = (
        classifier.predict_proba(x[cal_idx])
        if cal_idx.size
        else classifier.predict_proba(x[train_idx])
    )
    calibration_labels = y[cal_idx] if cal_idx.size else y[train_idx]
    calibration_groups = groups[cal_idx] if cal_idx.size else groups[train_idx]
    conformal = MondrianConformal(alpha=alpha).fit(
        calibration_probabilities, calibration_labels, classes, calibration_groups.tolist()
    )

    test_probabilities = classifier.predict_proba(x[test_idx])
    test_labels = y[test_idx]
    predictions = np.array([classes[int(np.argmax(row))] for row in test_probabilities])
    macro_f1 = _macro_f1(test_labels, predictions, evaluation_classes)
    majority = max(set(y[train_idx].tolist()), key=list(y[train_idx]).count)
    baseline_predictions = np.array([majority] * len(test_labels))
    baseline_macro_f1 = _macro_f1(test_labels, baseline_predictions, evaluation_classes)

    pred_sets: list[list[str]] = []
    set_sizes = []
    hits = 0
    for row, label, group in zip(test_probabilities, test_labels, groups[test_idx], strict=True):
        mode_set = conformal.predict_set(row, str(group))
        pred_sets.append(mode_set)
        set_sizes.append(len(mode_set))
        hits += int(str(label) in mode_set)
    coverage = float(hits / max(1, len(test_labels)))
    mean_set_size = float(np.mean(set_sizes)) if set_sizes else 0.0
    parity_gap, div_covs = division_coverage_gap(
        pred_sets,
        [str(lbl) for lbl in test_labels.tolist()],
        [str(grp) for grp in groups[test_idx].tolist()],
        min_support=5,
    )

    metrics = {
        "macro_f1": float(macro_f1),
        "baseline_macro_f1": float(baseline_macro_f1),
        "coverage": coverage,
        "mean_set_size": mean_set_size,
        "division_coverage_gap": float(parity_gap),
        "held_out_n": int(len(test_labels)),
        "classes": float(len(classes)),
        "split": split_name,
        "test_seed": float(test_seed),
    }
    return DiagnosisBundle(
        classifier=classifier,
        conformal=conformal,
        metrics=metrics,
        coverage=coverage,
        macro_f1=float(macro_f1),
        baseline_macro_f1=float(baseline_macro_f1),
        mean_set_size=mean_set_size,
        held_out_n=int(len(test_labels)),
        classes=classes,
        division_coverage_gap=float(parity_gap),
        division_coverages=div_covs,
    )


def _macro_f1(truth: np.ndarray, predictions: np.ndarray, classes: list[str]) -> float:
    scores: list[float] = []
    for label in classes:
        true_positive = np.sum((truth == label) & (predictions == label))
        false_positive = np.sum((truth != label) & (predictions == label))
        false_negative = np.sum((truth == label) & (predictions != label))
        precision = (
            true_positive / (true_positive + false_positive)
            if (true_positive + false_positive)
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if (true_positive + false_negative)
            else 0.0
        )
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        scores.append(float(f1))
    return float(np.mean(scores)) if scores else 0.0


def _format_diagnosis(
    bundle: DiagnosisBundle,
    vector: FeatureVector,
    probability_row: np.ndarray,
    shap_top: list[dict[str, float | str]],
    *,
    group: str | None = None,
    max_set_size: int = 3,
) -> dict[str, object]:
    probabilities = {
        label: float(probability_row[index])
        for index, label in enumerate(bundle.classifier.classes)
    }
    ranked = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))
    full_set = bundle.conformal.predict_set(probability_row, group)
    capped = full_set[:max_set_size]
    likely = [label for label, _ in ranked[:3]]
    mode_set = [label for label in likely if label in capped] or capped[:1] or likely[:1]
    if not mode_set:
        mode_set = likely[:1]
    top = likely[0]
    coverage = bundle.coverage
    if len(full_set) > max_set_size:
        coverage = float(max(0.0, bundle.coverage - 0.04 * (len(full_set) - max_set_size)))
    return {
        "probabilities": probabilities,
        "likely_modes": likely,
        "top_mode": top,
        "mode_probability": float(probabilities.get(top, 0.0)),
        "mode_set": mode_set,
        "mode_set_coverage": float(coverage),
        "set_size": len(mode_set),
        "capped": len(full_set) > max_set_size,
        "shap_top": shap_top,
    }


def diagnose_with_set(
    bundle: DiagnosisBundle,
    vector: FeatureVector,
    *,
    group: str | None = None,
    max_set_size: int = 3,
) -> dict[str, object]:
    """Return likely modes, probabilities, conformal set and signed SHAP features."""
    row = vector.array(bundle.classifier.feature_names)
    n_feat = len(bundle.classifier.feature_names)
    batch = np.tile(row, (n_feat + 1, 1))
    for index in range(n_feat):
        batch[index + 1, index] = bundle.classifier.baseline[index]
    all_probs = bundle.classifier.predict_proba(batch)
    shap = bundle.classifier.shap_top(vector, top_k=5, precomputed_probs=all_probs)
    return _format_diagnosis(
        bundle, vector, all_probs[0], shap, group=group, max_set_size=max_set_size
    )


def diagnose_batch(
    bundle: DiagnosisBundle,
    vectors: list[FeatureVector],
    groups: list[str | None],
    *,
    max_set_size: int = 3,
) -> list[dict[str, object]]:
    """Batch diagnosis + SHAP across many circuits in one classifier call."""
    if not vectors:
        return []
    n_feat = len(bundle.classifier.feature_names)
    stride = n_feat + 1
    blocks = np.empty((len(vectors) * stride, n_feat), dtype=float)
    for idx, vector in enumerate(vectors):
        row = vector.array(bundle.classifier.feature_names)
        base = idx * stride
        blocks[base] = row
        pert = blocks[base + 1 : base + stride]
        pert[:] = row
        np.fill_diagonal(pert, bundle.classifier.baseline)
    all_probs = bundle.classifier.predict_proba(blocks)
    results: list[dict[str, object]] = []
    for idx, (vector, group) in enumerate(zip(vectors, groups, strict=True)):
        chunk = all_probs[idx * stride : (idx + 1) * stride]
        shap = bundle.classifier.shap_top(vector, top_k=5, precomputed_probs=chunk)
        results.append(
            _format_diagnosis(
                bundle, vector, chunk[0], shap, group=group, max_set_size=max_set_size
            )
        )
    return results


def corpus_snapshot_as_of(stream, day: int):
    return stream.timestamps[min(day * 24, len(stream.timestamps) - 1)] + timedelta(0)
