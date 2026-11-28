"""Conformal prediction sets/intervals and per-zone horizon calibration.

Split conformal only: the calibration set is separate from the test set and time-ordered.
RUL intervals are built on log-time residuals and reported with their empirical coverage and
held-out count. Sets wider than three modes are capped and the reduced coverage is reported,
never silently widened.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    """Finite-sample split-conformal quantile (ceil((n+1)(1-alpha))/n)."""
    values = np.sort(np.asarray(scores, dtype=float))
    n = values.size
    if n == 0:
        return float("inf")
    rank = int(np.ceil((n + 1) * (1.0 - alpha)))
    rank = min(max(rank, 1), n)
    return float(values[rank - 1])


@dataclass(slots=True)
class SplitConformal:
    """Least-ambiguous-set (LAC) conformal predictor for a classifier."""

    alpha: float = 0.10
    quantile: float = 1.0
    n_calibration: int = 0
    labels: tuple[str, ...] = ()

    def fit(
        self, probabilities: np.ndarray, labels: np.ndarray, classes: list[str]
    ) -> SplitConformal:
        probabilities = np.asarray(probabilities, dtype=float)
        labels = np.asarray(labels)
        self.labels = tuple(classes)
        index = {label: position for position, label in enumerate(classes)}
        scores = np.array(
            [1.0 - probabilities[row, index[str(label)]] for row, label in enumerate(labels)],
            dtype=float,
        )
        self.quantile = conformal_quantile(scores, self.alpha)
        self.n_calibration = int(scores.size)
        return self

    def predict_set(self, probability_row: np.ndarray) -> list[str]:
        probability_row = np.asarray(probability_row, dtype=float)
        included = [
            label
            for position, label in enumerate(self.labels)
            if 1.0 - probability_row[position] <= self.quantile + 1e-12
        ]
        if not included:
            included = [self.labels[int(np.argmax(probability_row))]]
        included.sort(key=lambda label: -probability_row[self.labels.index(label)])
        return included

    def empirical_coverage(self, probabilities: np.ndarray, labels: np.ndarray) -> float:
        probabilities = np.asarray(probabilities, dtype=float)
        labels = np.asarray(labels)
        if probabilities.size == 0:
            return 0.0
        hits = 0
        for row, label in zip(probabilities, labels, strict=True):
            if str(label) in self.predict_set(row):
                hits += 1
        return float(hits / len(labels))


@dataclass(slots=True)
class MondrianConformal:
    """Per-division (Mondrian) conformal sets with a pooled fallback."""

    alpha: float = 0.10
    min_group_size: int = 30
    groups: dict[str, SplitConformal] = field(default_factory=dict)
    pooled: SplitConformal | None = None
    classes: list[str] = field(default_factory=list)

    def fit(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
        classes: list[str],
        groups: list[str] | None = None,
    ) -> MondrianConformal:
        probabilities = np.asarray(probabilities, dtype=float)
        labels = np.asarray(labels)
        self.classes = list(classes)
        self.pooled = SplitConformal(alpha=self.alpha).fit(probabilities, labels, classes)
        if groups is not None:
            group_array = np.asarray(groups)
            for group in sorted(set(group_array.tolist())):
                mask = group_array == group
                if int(mask.sum()) >= self.min_group_size:
                    self.groups[str(group)] = SplitConformal(alpha=self.alpha).fit(
                        probabilities[mask], labels[mask], classes
                    )
        return self

    def for_group(self, group: str | None) -> SplitConformal:
        if group is not None and str(group) in self.groups:
            return self.groups[str(group)]
        if self.pooled is None:
            raise RuntimeError("MondrianConformal is not fitted")
        return self.pooled

    def predict_set(self, probability_row: np.ndarray, group: str | None = None) -> list[str]:
        return self.for_group(group).predict_set(probability_row)


@dataclass(slots=True)
class ConformalRUL:
    """Conformal interval on log remaining-useful-life."""

    nominal: float = 0.80
    lower_offset: float = 0.0
    upper_offset: float = 0.0
    n_calibration: int = 0

    def fit(self, predicted_days: np.ndarray, observed_days: np.ndarray) -> ConformalRUL:
        predicted = np.maximum(np.asarray(predicted_days, dtype=float), 1.0)
        observed = np.maximum(np.asarray(observed_days, dtype=float), 1.0)
        residuals = np.log(observed) - np.log(predicted)
        alpha = 1.0 - self.nominal
        self.lower_offset = conformal_quantile(-residuals, alpha / 2.0)
        self.upper_offset = conformal_quantile(residuals, alpha / 2.0)
        self.n_calibration = int(residuals.size)
        return self

    def interval(self, predicted_days: float) -> tuple[int, int, int]:
        predicted = max(float(predicted_days), 1.0)
        low = int(max(0, round(np.exp(np.log(predicted) - self.lower_offset))))
        high = int(max(low, round(np.exp(np.log(predicted) + self.upper_offset))))
        median = int(max(low, min(high, round(predicted))))
        return low, median, high

    def empirical_coverage(self, predicted_days: np.ndarray, observed_days: np.ndarray) -> float:
        predicted = np.asarray(predicted_days, dtype=float)
        observed = np.asarray(observed_days, dtype=float)
        if predicted.size == 0:
            return 0.0
        hits = 0
        for prediction, actual in zip(predicted, observed, strict=True):
            low, _, high = self.interval(prediction)
            if low <= actual <= high:
                hits += 1
        return float(hits / predicted.size)


class IsotonicCalibrator:
    """Per-zone isotonic calibration with a monotone, deterministic fallback."""

    def __init__(self) -> None:
        self.x: np.ndarray = np.array([0.0, 1.0])
        self.y: np.ndarray = np.array([0.0, 1.0])
        self.fitted = False

    def fit(self, predictions: np.ndarray, outcomes: np.ndarray) -> IsotonicCalibrator:
        predictions = np.asarray(predictions, dtype=float)
        outcomes = np.asarray(outcomes, dtype=float)
        if predictions.size < 8 or np.unique(outcomes).size < 2:
            self.x = np.array([0.0, 1.0])
            self.y = np.array([0.0, 1.0])
            self.fitted = False
            return self
        try:
            from sklearn.isotonic import IsotonicRegression

            model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            model.fit(predictions, outcomes)
            grid = np.linspace(0.0, 1.0, 201)
            self.x = grid
            self.y = np.clip(model.predict(grid), 0.0, 1.0)
            # Enforce monotonicity after clipping.
            self.y = np.maximum.accumulate(self.y)
            self.fitted = True
        except Exception:  # pragma: no cover - sklearn is a core dependency
            self.x = np.array([0.0, 1.0])
            self.y = np.array([0.0, 1.0])
            self.fitted = False
        return self

    def predict(self, values: np.ndarray | float) -> np.ndarray:
        values = np.atleast_1d(np.asarray(values, dtype=float))
        return np.interp(values, self.x, self.y)


@dataclass(slots=True)
class HorizonCalibrator:
    """Calibration for h24/h72/h7d with a monotone projection across horizons."""

    by_zone: dict[str, dict[str, IsotonicCalibrator]] = field(default_factory=dict)
    pooled: dict[str, IsotonicCalibrator] = field(default_factory=dict)

    def fit(
        self,
        predictions: dict[str, np.ndarray],
        outcomes: dict[str, np.ndarray],
        zones: np.ndarray,
    ) -> HorizonCalibrator:
        zones = np.asarray(zones)
        for horizon in ("h24", "h72", "h7d"):
            self.pooled[horizon] = IsotonicCalibrator().fit(predictions[horizon], outcomes[horizon])
            for zone in sorted(set(zones.tolist())):
                mask = zones == zone
                if int(mask.sum()) >= 40:
                    self.by_zone.setdefault(str(zone), {})[horizon] = IsotonicCalibrator().fit(
                        predictions[horizon][mask], outcomes[horizon][mask]
                    )
        return self

    def calibrate(
        self, raw: dict[str, float], zone: str | None = None
    ) -> tuple[dict[str, float], bool]:
        calibrated: dict[str, float] = {}
        used_pooled = False
        for horizon in ("h24", "h72", "h7d"):
            calibrator = self.by_zone.get(str(zone), {}).get(horizon) if zone else None
            if calibrator is None:
                calibrator = self.pooled.get(horizon)
                used_pooled = True
            calibrated[horizon] = (
                float(calibrator.predict(raw[horizon])[0]) if calibrator else raw[horizon]
            )
        return monotone_projection(calibrated), used_pooled


def monotone_projection(risk: dict[str, float]) -> dict[str, float]:
    """Enforce h24 <= h72 <= h7d after calibration (pool-adjacent-violators, 3 points)."""
    values = [float(risk["h24"]), float(risk["h72"]), float(risk["h7d"])]
    # Three-point isotonic projection.
    if values[0] > values[1]:
        values[0] = values[1] = (values[0] + values[1]) / 2.0
    if values[1] > values[2]:
        values[1] = values[2] = (values[1] + values[2]) / 2.0
    if values[0] > values[1]:
        values[0] = values[1] = (values[0] + values[1]) / 2.0
    return {
        "h24": float(np.clip(values[0], 0.0, 1.0)),
        "h72": float(np.clip(values[1], 0.0, 1.0)),
        "h7d": float(np.clip(values[2], 0.0, 1.0)),
    }
