"""Metric definitions from spec Appendix A, implemented against hand-checkable fixtures."""

from __future__ import annotations

import numpy as np


def expected_calibration_error(
    predictions: np.ndarray, outcomes: np.ndarray, *, bins: int = 10
) -> float:
    """ECE over equal-frequency bins: sum (n_b/N) * |observed - predicted|."""
    predictions = np.asarray(predictions, dtype=float)
    outcomes = np.asarray(outcomes, dtype=float)
    if predictions.size == 0:
        return 0.0
    order = np.argsort(predictions, kind="stable")
    predictions = predictions[order]
    outcomes = outcomes[order]
    chunks = np.array_split(np.arange(predictions.size), min(bins, predictions.size))
    error = 0.0
    for chunk in chunks:
        if chunk.size == 0:
            continue
        predicted = float(np.mean(predictions[chunk]))
        observed = float(np.mean(outcomes[chunk]))
        error += (chunk.size / predictions.size) * abs(observed - predicted)
    return float(error)


def interval_coverage(low: np.ndarray, high: np.ndarray, observed: np.ndarray) -> float:
    """Share of observations inside inclusive intervals."""
    low = np.asarray(low, dtype=float)
    high = np.asarray(high, dtype=float)
    observed = np.asarray(observed, dtype=float)
    if observed.size == 0:
        return 0.0
    return float(np.mean((observed >= low) & (observed <= high)))


def set_coverage(sets: list[list[str]], labels: list[str]) -> float:
    """Share of labels contained in their predicted set."""
    if not labels:
        return 0.0
    return float(
        np.mean([label in prediction for prediction, label in zip(sets, labels, strict=True)])
    )


def precision_at_k(scores: np.ndarray, labels: np.ndarray, k: int = 10) -> float:
    """Share of the top-k worklist items that are positive."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=float)
    if labels.size == 0:
        return 0.0
    order = np.argsort(-scores, kind="stable")[: min(k, labels.size)]
    return float(np.mean(labels[order]))


def average_precision(scores: np.ndarray, labels: np.ndarray) -> float:
    """PR-AUC as average precision."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    if labels.size == 0 or labels.sum() == 0:
        return 0.0
    order = np.argsort(-scores, kind="stable")
    labels = labels[order]
    hits = 0
    precision_sum = 0.0
    for rank, label in enumerate(labels, start=1):
        if label:
            hits += 1
            precision_sum += hits / rank
    return float(precision_sum / labels.sum())


def brier_score(predictions: np.ndarray, outcomes: np.ndarray) -> float:
    predictions = np.asarray(predictions, dtype=float)
    outcomes = np.asarray(outcomes, dtype=float)
    if predictions.size == 0:
        return 0.0
    return float(np.mean((predictions - outcomes) ** 2))


def population_stability_index(
    reference: np.ndarray, current: np.ndarray, *, bins: int = 10, epsilon: float = 1e-6
) -> float:
    """PSI between reference and current distributions."""
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    if reference.size == 0 or current.size == 0:
        return 0.0
    edges = np.quantile(reference, np.linspace(0.0, 1.0, bins + 1))
    edges[0] = -np.inf
    edges[-1] = np.inf
    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)
    ref_share = np.clip(ref_counts / max(reference.size, 1), epsilon, None)
    cur_share = np.clip(cur_counts / max(current.size, 1), epsilon, None)
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def c_index(risk_scores: np.ndarray, durations: np.ndarray, events: np.ndarray) -> float:
    """Harrell's concordance index with right-censoring."""
    risk_scores = np.asarray(risk_scores, dtype=float)
    durations = np.asarray(durations, dtype=float)
    events = np.asarray(events, dtype=int)
    concordant = 0.0
    comparable = 0
    for i in range(len(durations)):
        if events[i] != 1:
            continue
        for j in range(len(durations)):
            if i == j:
                continue
            if durations[j] > durations[i] or (durations[j] == durations[i] and events[j] == 0):
                comparable += 1
                if risk_scores[i] > risk_scores[j]:
                    concordant += 1
                elif risk_scores[i] == risk_scores[j]:
                    concordant += 0.5
    return float(concordant / comparable) if comparable else 0.5


def macro_f1(truth: np.ndarray, predictions: np.ndarray, classes: list[str]) -> float:
    truth = np.asarray(truth)
    predictions = np.asarray(predictions)
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
        scores.append(
            float(2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        )
    return float(np.mean(scores)) if scores else 0.0


def bootstrap_ci(
    values: np.ndarray,
    *,
    statistic=np.mean,
    n_bootstrap: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap confidence interval."""
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    samples = np.array(
        [statistic(rng.choice(values, size=values.size, replace=True)) for _ in range(n_bootstrap)]
    )
    return (float(np.quantile(samples, alpha / 2)), float(np.quantile(samples, 1 - alpha / 2)))


def _coverage_gap_by_group(
    covered: list[bool], groups: list[str], *, min_support: int = 5
) -> tuple[float, dict[str, float]]:
    """Compute max-min subgroup coverage across groups meeting ``min_support``."""
    if not covered or len(covered) != len(groups):
        return (0.0, {})
    buckets: dict[str, list[bool]] = {}
    for flag, group in zip(covered, groups, strict=True):
        buckets.setdefault(str(group), []).append(bool(flag))
    per_group = {
        group: float(np.mean(flags))
        for group, flags in sorted(buckets.items())
        if len(flags) >= min_support
    }
    if len(per_group) < 2:
        return (0.0, per_group)
    values = list(per_group.values())
    return (float(max(values) - min(values)), per_group)


def division_coverage_gap(
    sets: list[list[str]],
    labels: list[str],
    divisions: list[str],
    *,
    min_support: int = 5,
) -> tuple[float, dict[str, float]]:
    """Max-min conformal set coverage gap across railway divisions (spec §12.1 / §13)."""
    covered = [label in pred for pred, label in zip(sets, labels, strict=True)]
    return _coverage_gap_by_group(covered, divisions, min_support=min_support)


def division_interval_coverage_gap(
    low: np.ndarray,
    high: np.ndarray,
    observed: np.ndarray,
    divisions: list[str],
    *,
    min_support: int = 5,
) -> tuple[float, dict[str, float]]:
    """Max-min conformal RUL interval coverage gap across railway divisions."""
    low_arr = np.asarray(low, dtype=float)
    high_arr = np.asarray(high, dtype=float)
    obs_arr = np.asarray(observed, dtype=float)
    covered = [bool(lo <= y <= hi) for lo, hi, y in zip(low_arr, high_arr, obs_arr, strict=True)]
    return _coverage_gap_by_group(covered, divisions, min_support=min_support)
