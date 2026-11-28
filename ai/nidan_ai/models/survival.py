"""T4 survival and remaining useful life with censoring, frailty proxies and conformal RUL.

The model is a Cox proportional-hazards fit with a Weibull baseline reconstructed from the
Breslow estimator. Right-censored assets contribute to the risk sets; maintenance is carried
as a time-varying covariate proxy (days since repair, repair count). Intervals are conformal
on log-time residuals, and coverage is measured on held-out event outcomes only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from nidan_ai.bench.generator import generate
from nidan_ai.bench.scenarios import SCENARIO_NAMES
from nidan_ai.data.canonical import from_bench
from nidan_ai.data.features import FeatureVector, build_features, context_from_asset
from nidan_ai.models.conformal import ConformalRUL

SURVIVAL_FEATURES: tuple[str, ...] = (
    "margin_ratio",
    "margin_slope_7d",
    "margin_slope_28d",
    "gb_ratio",
    "twin_z",
    "drop_p95_ms",
    "age_ratio",
    "days_since_repair",
    "repair_count_12m",
    "rain_72h",
    "harmonic_mv_24h",
    "feed_min_24h",
    "flicker_rate_24h",
    "step_score_24h",
    "trust_score",
)


@dataclass(slots=True)
class SurvivalDataset:
    """Time-to-event dataset with right-censoring."""

    vectors: list[FeatureVector]
    durations: np.ndarray
    events: np.ndarray
    groups: np.ndarray
    asset_ids: list[str]
    seeds: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    stations: np.ndarray = field(default_factory=lambda: np.array([], dtype=str))


@dataclass(slots=True)
class CoxWeibull:
    """Cox partial likelihood with division frailty and a Weibull baseline."""

    coefficients: np.ndarray = field(default_factory=lambda: np.zeros(0))
    center: np.ndarray = field(default_factory=lambda: np.zeros(0))
    scale: np.ndarray = field(default_factory=lambda: np.ones(0))
    shape: float = 1.0
    baseline_scale: float = 100.0
    frailty: dict[str, float] = field(default_factory=dict)
    feature_names: tuple[str, ...] = SURVIVAL_FEATURES

    def _matrix(self, vectors: list[FeatureVector]) -> np.ndarray:
        return np.vstack([vector.array(self.feature_names) for vector in vectors])

    def fit(
        self,
        vectors: list[FeatureVector],
        durations: np.ndarray,
        events: np.ndarray,
        *,
        groups: np.ndarray | list[str] | None = None,
        l2: float = 2.0,
        frailty_prior: float = 5.0,
        iterations: int = 60,
    ) -> CoxWeibull:
        x = self._matrix(vectors)
        durations = np.asarray(durations, dtype=float)
        events = np.asarray(events, dtype=int)
        self.center = np.median(x, axis=0)
        self.scale = np.std(x, axis=0)
        self.scale = np.where(self.scale > 1e-9, self.scale, 1.0)
        z = (x - self.center) / self.scale
        n, p = z.shape
        beta = np.zeros(p)
        for _ in range(iterations):
            risk = z @ beta
            order = np.argsort(-durations, kind="stable")
            z_sorted = z[order]
            durations_sorted = durations[order]
            events_sorted = events[order]
            risk_sorted = risk[order]
            # Cumulative risk-set sums from the longest duration downwards.
            exp_risk = np.exp(np.clip(risk_sorted, -30, 30))
            cumulative = np.cumsum(exp_risk)
            cumulative_z = np.cumsum(z_sorted * exp_risk[:, None], axis=0)
            gradient = np.zeros(p)
            hessian = np.zeros((p, p))
            for index in range(n):
                if events_sorted[index] != 1:
                    continue
                # Risk set is all rows with duration >= this duration (already earlier in order).
                last = index
                while last + 1 < n and durations_sorted[last + 1] >= durations_sorted[index]:
                    last += 1
                total = cumulative[last]
                if total <= 0:
                    continue
                mean = cumulative_z[last] / total
                gradient += z_sorted[index] - mean
                second = (z_sorted * exp_risk[:, None])[: last + 1]
                covariance = (second.T @ z_sorted[: last + 1]) / total - np.outer(mean, mean)
                hessian -= covariance
            gradient -= l2 * beta
            hessian -= l2 * np.eye(p)
            try:
                step = np.linalg.solve(-hessian, gradient)
            except np.linalg.LinAlgError:
                step = gradient * 0.01
            step_norm = float(np.max(np.abs(step))) if step.size else 0.0
            beta += np.clip(step, -0.5, 0.5)
            if step_norm < 1e-7:
                break
        self.coefficients = beta
        self._fit_baseline(z, durations, events)
        self._fit_frailty(z, durations, events, groups=groups, prior=frailty_prior)
        return self

    def _fit_frailty(
        self,
        z: np.ndarray,
        durations: np.ndarray,
        events: np.ndarray,
        *,
        groups: np.ndarray | list[str] | None,
        prior: float = 5.0,
    ) -> None:
        self.frailty = {}
        if groups is None:
            return
        group_arr = np.asarray(groups, dtype=str)
        risk = z @ self.coefficients
        base_cum = (np.maximum(durations, 0.0) / max(self.baseline_scale, 1e-9)) ** self.shape
        expected = base_cum * np.exp(np.clip(risk, -30, 30))
        for group in sorted(set(group_arr.tolist())):
            mask = group_arr == group
            obs_g = float(np.sum(events[mask] == 1))
            exp_g = float(np.sum(expected[mask]))
            u = float(np.log((obs_g + prior) / (exp_g + prior)))
            self.frailty[str(group)] = float(np.clip(u, -1.5, 1.5))

    def _fit_baseline(self, z: np.ndarray, durations: np.ndarray, events: np.ndarray) -> None:
        risk = z @ self.coefficients
        exp_risk = np.exp(np.clip(risk, -30, 30))
        event_times = np.sort(np.unique(durations[events == 1]))
        cumulative = 0.0
        times: list[float] = []
        hazards: list[float] = []
        for time in event_times:
            at_risk_sum = float(np.sum(exp_risk[durations >= time]))
            deaths = float(np.sum((durations == time) & (events == 1)))
            if at_risk_sum <= 1e-12:
                continue
            cumulative += deaths / at_risk_sum
            times.append(float(time))
            hazards.append(float(cumulative))
        if len(times) >= 2 and np.all(np.array(hazards) > 0):
            log_t = np.log(np.array(times))
            log_h = np.log(np.array(hazards))
            slope, intercept = np.polyfit(log_t, log_h, 1)
            self.shape = float(max(0.25, min(5.0, slope)))
            self.baseline_scale = float(np.exp(-intercept / max(self.shape, 1e-6)))
        else:
            self.shape = 1.0
            self.baseline_scale = float(max(np.median(durations), 1.0))

    def risk_score(self, vector: FeatureVector, *, group: str | None = None) -> float:
        row = (vector.array(self.feature_names) - self.center) / self.scale
        frailty = self.frailty.get(str(group), 0.0) if group is not None else 0.0
        return float(row @ self.coefficients + frailty)

    def predict_median_days(self, vector: FeatureVector, *, group: str | None = None) -> float:
        risk = self.risk_score(vector, group=group)
        target = np.log(2.0) / max(np.exp(np.clip(risk, -30, 30)), 1e-9)
        days = self.baseline_scale * target ** (1.0 / max(self.shape, 1e-6))
        return float(np.clip(days, 0.0, 3650.0))

    def survival(self, vector: FeatureVector, days: float, *, group: str | None = None) -> float:
        risk = self.risk_score(vector, group=group)
        hazard = (max(days, 0.0) / max(self.baseline_scale, 1e-9)) ** self.shape
        return float(np.exp(-hazard * np.exp(np.clip(risk, -30, 30))))


def c_index(risk_scores: np.ndarray, durations: np.ndarray, events: np.ndarray) -> float:
    """Harrell's concordance index with right-censoring."""
    risk_scores = np.asarray(risk_scores, dtype=float)
    durations = np.asarray(durations, dtype=float)
    events = np.asarray(events, dtype=int)
    concordant = 0.0
    comparable = 0.0
    n = len(durations)
    for i in range(n):
        if events[i] != 1:
            continue
        for j in range(n):
            if i == j:
                continue
            if durations[j] > durations[i] or (durations[j] == durations[i] and events[j] == 0):
                comparable += 1
                if risk_scores[i] > risk_scores[j]:
                    concordant += 1
                elif risk_scores[i] == risk_scores[j]:
                    concordant += 0.5
    return float(concordant / comparable) if comparable else 0.5


@dataclass(slots=True)
class SurvivalBundle:
    """Fitted survival model plus measured discrimination and interval coverage."""

    model: CoxWeibull
    conformal: ConformalRUL
    c_index: float
    constant_hazard_c_index: float
    coverage: float
    held_out_n: int
    calibration_n: int
    metrics: dict[str, float] = field(default_factory=dict)


def build_survival_corpus(
    *,
    seeds: tuple[int, ...] = (42, 43, 44, 99),
    scenarios: tuple[str, ...] = SCENARIO_NAMES,
) -> SurvivalDataset:
    """Build a time-to-event corpus from the bench, with right-censoring."""
    vectors: list[FeatureVector] = []
    durations: list[float] = []
    events: list[int] = []
    groups: list[str] = []
    asset_ids: list[str] = []
    seeds_out: list[int] = []
    stations_out: list[str] = []
    for scenario_name in scenarios:
        for seed in seeds:
            stream = generate(scenario_name, seed=seed)
            dataset = from_bench(stream, as_of=stream.timestamps[-1])
            for asset in stream.assets:
                event = stream.event_for(asset.asset_id)
                event_day = event.event_day if event is not None else stream.scenario_def.days
                context = context_from_asset(asset)
                for snapshot_day in (10, 20, 30, 40):
                    if snapshot_day >= event_day or snapshot_day >= stream.scenario_def.days - 1:
                        continue
                    vector = build_features(
                        dataset.assets[asset.asset_id],
                        context,
                        stream.timestamps[snapshot_day * 24],
                        clock_offset_minutes=stream.clock_offsets_minutes.get(asset.asset_id, 0),
                    )
                    vectors.append(vector)
                    durations.append(float(event_day - snapshot_day))
                    events.append(1 if event is not None else 0)
                    groups.append(asset.division)
                    asset_ids.append(asset.asset_id)
                    seeds_out.append(int(seed))
                    stations_out.append(asset.station)
    return SurvivalDataset(
        vectors=vectors,
        durations=np.array(durations, dtype=float),
        events=np.array(events, dtype=int),
        groups=np.array(groups),
        asset_ids=asset_ids,
        seeds=np.array(seeds_out, dtype=int),
        stations=np.array(stations_out),
    )


def _group_split_indices(
    dataset: SurvivalDataset, *, seed: int, test_seed: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Split without leaking snapshots of the same asset across train/cal/test."""
    n = len(dataset.vectors)
    if dataset.seeds.size == n and len(set(dataset.seeds.tolist())) >= 3:
        test_idx = np.flatnonzero(dataset.seeds == test_seed)
        pool = np.flatnonzero(dataset.seeds != test_seed)
        other_seeds = sorted(set(dataset.seeds[pool].tolist()))
        if test_idx.size >= 15 and len(other_seeds) >= 2:
            cal_seed = other_seeds[-1]
            train_idx = pool[dataset.seeds[pool] != cal_seed]
            cal_idx = pool[dataset.seeds[pool] == cal_seed]
            return train_idx, cal_idx, test_idx, f"seed-held-out:{test_seed}"
    unique_assets = sorted(set(dataset.asset_ids))
    rng = np.random.default_rng(seed)
    shuffled = list(unique_assets)
    rng.shuffle(shuffled)
    n_train = max(1, int(0.60 * len(shuffled)))
    n_cal = max(1, int(0.20 * len(shuffled)))
    train_assets = set(shuffled[:n_train])
    cal_assets = set(shuffled[n_train : n_train + n_cal])
    train_idx = np.array([i for i, aid in enumerate(dataset.asset_ids) if aid in train_assets])
    cal_idx = np.array([i for i, aid in enumerate(dataset.asset_ids) if aid in cal_assets])
    test_idx = np.array(
        [i for i, aid in enumerate(dataset.asset_ids) if aid not in train_assets | cal_assets]
    )
    return train_idx, cal_idx, test_idx, "asset-grouped"


def train_survival_model(
    dataset: SurvivalDataset | None = None,
    *,
    seed: int = 42,
    test_seed: int = 99,
) -> SurvivalBundle:
    """Fit Cox-Weibull with division frailty and conformal RUL on held-out splits."""
    dataset = dataset or build_survival_corpus(seeds=(42, 43, 44, test_seed))
    n = len(dataset.vectors)
    if n < 20:
        raise ValueError("Survival corpus is too small")
    train_idx, cal_idx, test_idx, split_name = _group_split_indices(
        dataset, seed=seed, test_seed=test_seed
    )
    model = CoxWeibull().fit(
        [dataset.vectors[i] for i in train_idx],
        dataset.durations[train_idx],
        dataset.events[train_idx],
        groups=dataset.groups[train_idx],
    )
    risk_train = np.array(
        [model.risk_score(dataset.vectors[i], group=str(dataset.groups[i])) for i in train_idx]
    )
    c_index_train = c_index(risk_train, dataset.durations[train_idx], dataset.events[train_idx])
    risk_test = np.array(
        [model.risk_score(dataset.vectors[i], group=str(dataset.groups[i])) for i in test_idx]
    )
    c_index_test = c_index(risk_test, dataset.durations[test_idx], dataset.events[test_idx])

    # Conformal RUL calibration on event outcomes only.
    cal_events = [i for i in cal_idx if dataset.events[i] == 1]
    if len(cal_events) < 10:
        cal_events = [i for i in train_idx if dataset.events[i] == 1]
    predicted_cal = np.array(
        [
            model.predict_median_days(dataset.vectors[i], group=str(dataset.groups[i]))
            for i in cal_events
        ]
    )
    observed_cal = dataset.durations[cal_events]
    conformal = ConformalRUL(nominal=0.80).fit(predicted_cal, observed_cal)

    test_events = [i for i in test_idx if dataset.events[i] == 1]
    predicted_test = np.array(
        [
            model.predict_median_days(dataset.vectors[i], group=str(dataset.groups[i]))
            for i in test_events
        ]
    )
    observed_test = dataset.durations[test_events]
    coverage = (
        conformal.empirical_coverage(predicted_test, observed_test) if len(test_events) else 0.0
    )
    constant_c = c_index(
        np.zeros(len(test_idx)), dataset.durations[test_idx], dataset.events[test_idx]
    )
    return SurvivalBundle(
        model=model,
        conformal=conformal,
        c_index=float(c_index_test),
        constant_hazard_c_index=float(constant_c),
        coverage=float(coverage),
        held_out_n=int(len(test_events)),
        calibration_n=int(len(cal_events)),
        metrics={
            "c_index_train": float(c_index_train),
            "c_index_test": float(c_index_test),
            "constant_hazard_c_index": float(constant_c),
            "rul_coverage": float(coverage),
            "held_out_n": int(len(test_events)),
            "calibration_n": int(len(cal_events)),
            "split": split_name,
        },
    )


def rul_interval(
    bundle: SurvivalBundle, vector: FeatureVector, *, group: str | None = None
) -> tuple[int, int, int]:
    """Integer p10/median/p90 days, ordered and clamped at zero."""
    median = bundle.model.predict_median_days(vector, group=group)
    low, mid, high = bundle.conformal.interval(median)
    return int(max(0, low)), int(max(0, mid)), int(max(mid, high))
