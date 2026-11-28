"""T1 anomaly detection: context baseline, CUSUM/EWMA, tiny autoencoder and fusion.

The detector answers "is this circuit abnormal for itself, given weather and traffic?" It
combines a robust weather-conditioned residual, a two-sided CUSUM/EWMA, a small deterministic
autoencoder reconstruction error and an isolation forest. Persistence is counted from stored
history, never drawn at random.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from nidan_ai.data.features import MODEL_FEATURES, FeatureVector


@dataclass(slots=True)
class AnomalyScore:
    """Fused anomaly output for one asset at one snapshot."""

    score: float
    persistence: int
    drivers: list[str]
    components: dict[str, float] = field(default_factory=dict)
    trend_alarm: bool = False


class RobustScaler:
    """Median/MAD scaler; deterministic and resistant to outliers."""

    def __init__(self) -> None:
        self.center = np.zeros(0)
        self.scale = np.ones(0)

    def fit(self, x: np.ndarray) -> RobustScaler:
        x = np.asarray(x, dtype=float)
        if x.ndim == 1:
            x = x.reshape(-1, 1)
        self.center = np.median(x, axis=0)
        mad = np.median(np.abs(x - self.center), axis=0) * 1.4826
        self.scale = np.where(mad > 1e-9, mad, 1.0)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        return (x - self.center) / self.scale


class TinyAutoencoder:
    """A small deterministic autoencoder implemented in NumPy.

    Fixed seed, fixed epoch count, float64. It is deliberately tiny: the point is a stable
    self-supervised residual, not a deep model.
    """

    def __init__(
        self,
        n_features: int,
        *,
        hidden: int = 10,
        seed: int = 42,
        epochs: int = 220,
        learning_rate: float = 0.02,
    ) -> None:
        self.n_features = int(n_features)
        self.hidden = int(hidden)
        self.seed = int(seed)
        self.epochs = int(epochs)
        self.learning_rate = float(learning_rate)
        rng = np.random.default_rng(self.seed)
        self.w1 = rng.normal(0.0, 0.1, (self.n_features, self.hidden))
        self.b1 = np.zeros(self.hidden)
        self.w2 = rng.normal(0.0, 0.1, (self.hidden, self.n_features))
        self.b2 = np.zeros(self.n_features)
        self.scaler = RobustScaler()
        self.residual_center = 0.0
        self.residual_scale = 1.0

    def _forward(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        hidden = np.tanh(x @ self.w1 + self.b1)
        output = hidden @ self.w2 + self.b2
        return hidden, output

    def fit(self, x: np.ndarray) -> TinyAutoencoder:
        x = np.asarray(x, dtype=float)
        self.scaler.fit(x)
        z = self.scaler.transform(x)
        m = z.shape[0]
        params = [self.w1, self.b1, self.w2, self.b2]
        moments = [np.zeros_like(param) for param in params]
        velocities = [np.zeros_like(param) for param in params]
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        for step in range(1, self.epochs + 1):
            hidden, output = self._forward(z)
            error = output - z
            grad_out = 2.0 * error / max(m, 1)
            grad_w2 = hidden.T @ grad_out
            grad_b2 = grad_out.sum(axis=0)
            grad_hidden = (grad_out @ self.w2.T) * (1.0 - hidden * hidden)
            grad_w1 = z.T @ grad_hidden
            grad_b1 = grad_hidden.sum(axis=0)
            grads = [grad_w1, grad_b1, grad_w2, grad_b2]
            for index, (param, grad) in enumerate(zip(params, grads, strict=True)):
                moments[index] = beta1 * moments[index] + (1 - beta1) * grad
                velocities[index] = beta2 * velocities[index] + (1 - beta2) * grad * grad
                m_hat = moments[index] / (1 - beta1**step)
                v_hat = velocities[index] / (1 - beta2**step)
                param -= self.learning_rate * m_hat / (np.sqrt(v_hat) + eps)
        residuals = self._residuals(z)
        self.residual_center = float(np.median(residuals))
        mad = float(np.median(np.abs(residuals - self.residual_center)) * 1.4826)
        self.residual_scale = mad if mad > 1e-9 else 1.0
        return self

    def _residuals(self, z: np.ndarray) -> np.ndarray:
        _, output = self._forward(z)
        return np.sqrt(np.mean((output - z) ** 2, axis=1))

    def score(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        residuals = self._residuals(self.scaler.transform(x))
        z = (residuals - self.residual_center) / self.residual_scale
        return 1.0 / (1.0 + np.exp(-(z - 2.5)))


class ContextBaseline:
    """Weather-conditioned robust baseline for relay margin."""

    def __init__(self) -> None:
        self.coefficients = np.zeros(3)
        self.residual_center = 0.0
        self.residual_scale = 1.0

    def fit(self, margin: np.ndarray, rain_72h: np.ndarray, temp: np.ndarray) -> ContextBaseline:
        margin = np.asarray(margin, dtype=float)
        design = np.column_stack(
            [np.ones(margin.size), np.asarray(rain_72h, float), np.asarray(temp, float)]
        )
        mask = np.all(np.isfinite(design), axis=1) & np.isfinite(margin)
        if mask.sum() >= 4:
            beta, *_ = np.linalg.lstsq(design[mask], margin[mask], rcond=None)
            self.coefficients = beta
        residuals = margin - design @ self.coefficients
        finite = residuals[np.isfinite(residuals)]
        self.residual_center = float(np.median(finite)) if finite.size else 0.0
        mad = (
            float(np.median(np.abs(finite - self.residual_center)) * 1.4826) if finite.size else 1.0
        )
        self.residual_scale = mad if mad > 1e-9 else 1.0
        return self

    def zscore(self, margin: float, rain_72h: float, temp: float) -> float:
        prediction = (
            self.coefficients[0] + self.coefficients[1] * rain_72h + self.coefficients[2] * temp
        )
        return float((margin - prediction - self.residual_center) / self.residual_scale)


class CusumEwma:
    """Two-sided CUSUM and EWMA over a standardised residual."""

    def __init__(self, *, drift: float = 0.5, threshold: float = 5.0, alpha: float = 0.2) -> None:
        self.drift = float(drift)
        self.threshold = float(threshold)
        self.alpha = float(alpha)
        self.ewma = 0.0
        self.cusum_pos = 0.0
        self.cusum_neg = 0.0

    def update(self, z: float) -> tuple[float, float]:
        self.ewma = self.alpha * z + (1.0 - self.alpha) * self.ewma
        self.cusum_pos = max(0.0, self.cusum_pos + z - self.drift)
        self.cusum_neg = max(0.0, self.cusum_neg - z - self.drift)
        return self.cusum_pos, self.cusum_neg


@dataclass(slots=True)
class AnomalyDetector:
    """Fitted fusion detector for one division."""

    autoencoder: TinyAutoencoder
    baseline: ContextBaseline
    isolation: object | None = None
    feature_names: tuple[str, ...] = MODEL_FEATURES
    threshold: float = 0.62
    _scaler: RobustScaler = field(default_factory=RobustScaler)

    @classmethod
    def fit(cls, healthy: list[FeatureVector], *, seed: int = 42) -> AnomalyDetector:
        if not healthy:
            raise ValueError("At least one healthy feature vector is required")
        matrix = np.vstack([vector.array(MODEL_FEATURES) for vector in healthy])
        autoencoder = TinyAutoencoder(matrix.shape[1], seed=seed).fit(matrix)
        baseline = ContextBaseline().fit(
            np.array([vector.get("margin_ratio") for vector in healthy]),
            np.array([vector.get("rain_72h") for vector in healthy]),
            np.array([vector.get("temp_mean_24h") for vector in healthy]),
        )
        isolation = None
        if matrix.shape[0] >= 24:
            try:
                from sklearn.ensemble import IsolationForest

                isolation = IsolationForest(
                    n_estimators=80,
                    contamination="auto",
                    random_state=seed,
                    n_jobs=1,
                ).fit(matrix)
            except Exception:  # pragma: no cover - optional robustness
                isolation = None
        return cls(autoencoder=autoencoder, baseline=baseline, isolation=isolation)

    def score(
        self,
        vector: FeatureVector,
        *,
        persistence: int = 0,
        tracker: CusumEwma | None = None,
    ) -> AnomalyScore:
        matrix = vector.array(self.feature_names).reshape(1, -1)
        auto = float(self.autoencoder.score(matrix)[0])
        context_z = self.baseline.zscore(
            vector.get("margin_ratio"),
            vector.get("rain_72h"),
            vector.get("temp_mean_24h"),
        )
        context_score = float(1.0 / (1.0 + np.exp(-(abs(context_z) - 2.0))))
        cusum_score = 0.0
        ewma_val = 0.0
        if tracker is not None:
            pos, neg = tracker.update(context_z)
            ewma_val = tracker.ewma
            cusum_score = float(min(1.0, max(pos, neg) / max(tracker.threshold, 1e-6)))
        isolation_score = 0.0
        if self.isolation is not None:
            raw = float(-self.isolation.score_samples(matrix)[0])
            isolation_score = float(1.0 / (1.0 + np.exp(-(raw - 0.55) * 12.0)))
        flicker = float(min(1.0, vector.get("flicker_rate_24h") / 4.0))
        slope = float(min(1.0, max(0.0, -vector.get("margin_slope_7d") / 0.8)))
        step = float(min(1.0, vector.get("step_score_24h") / 5.0))
        trust = float(vector.get("trust_score", 1.0))

        fused = (
            0.25 * context_score
            + 0.22 * auto
            + 0.15 * isolation_score
            + 0.12 * slope
            + 0.10 * flicker
            + 0.08 * step
            + 0.08 * cusum_score
        )
        # Low trust does not suppress the anomaly; it widens uncertainty and reduces rank.
        fused = float(np.clip(fused * (0.75 + 0.25 * trust), 0.0, 1.0))
        components = {
            "context_z": context_z,
            "context_score": context_score,
            "cusum_score": cusum_score,
            "ewma": ewma_val,
            "autoencoder": auto,
            "isolation_forest": isolation_score,
            "margin_slope": slope,
            "flicker": flicker,
            "step": step,
        }
        ranked = sorted(
            (
                (abs(context_z), "margin_ratio"),
                (auto, "relay_pct_24h"),
                (slope, "margin_slope_7d"),
                (flicker, "flicker_rate_24h"),
                (step, "step_score_24h"),
                (cusum_score, "twin_z"),
            ),
            reverse=True,
        )
        drivers = [name for _, name in ranked[:3]]
        return AnomalyScore(
            score=fused,
            persistence=int(persistence),
            drivers=drivers,
            components=components,
            trend_alarm=bool(
                vector.get("margin_slope_7d") < -0.3 and vector.get("margin_ratio") < 0.75
            ),
        )

    def score_series(
        self, vectors: list[FeatureVector], *, threshold: float | None = None
    ) -> list[AnomalyScore]:
        """Score a chronological sequence for one asset with CUSUM/EWMA and persistence."""
        thr = self.threshold if threshold is None else float(threshold)
        tracker = CusumEwma()
        history: list[float] = []
        results: list[AnomalyScore] = []
        for vector in vectors:
            prelim = self.score(vector, persistence=0, tracker=tracker)
            history.append(prelim.score)
            pers = persistence_from_history(history, thr)
            results.append(
                AnomalyScore(
                    score=prelim.score,
                    persistence=pers,
                    drivers=prelim.drivers,
                    components=prelim.components,
                    trend_alarm=prelim.trend_alarm,
                )
            )
        return results


def persistence_from_history(scores: list[float], threshold: float) -> int:
    """Count consecutive most-recent scores at or above ``threshold``."""
    count = 0
    for score in reversed(scores):
        if score >= threshold:
            count += 1
        else:
            break
    return count
