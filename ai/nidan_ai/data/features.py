"""Windowed, leakage-safe feature construction.

All windows end at the snapshot watermark. No future covariate, post-repair sample, closure
text, cause code or work-order outcome is ever used as an input. Feature names are stable
column names; human labels live beside them for the explanation layer.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from nidan_ai.data.canonical import AssetTelemetry, parse_utc
from nidan_ai.data.quality import QualityResult, assess_quality
from nidan_ai.physics.line import dry_current
from nidan_ai.physics.twin import TwinResult, run_twin


@dataclass(frozen=True, slots=True)
class AssetContext:
    """Design and maintenance context for one asset (never target-derived)."""

    asset_id: str
    station: str
    division: str
    route: str
    length_km: float
    rail_ohm_km: float
    dry_ballast_ohm_km: float
    feed_v: float
    source_ohm: float
    relay_ohm: float
    shunt_ohm: float
    relay_room: str
    supply_id: str
    cable_id: str
    weather_cell: str
    age_years: float
    codal_life_years: int
    traffic_per_day: int
    days_since_repair: int = 365
    repair_count_12m: int = 0
    last_repair_day: int | None = None

    @property
    def age_ratio(self) -> float:
        return float(self.age_years / max(self.codal_life_years, 1))

    def line_params(self):
        from nidan_ai.physics.line import LineParams

        return LineParams(
            length_km=self.length_km,
            rail_ohm_km=self.rail_ohm_km,
            feed_v=self.feed_v,
            source_ohm=self.source_ohm,
            relay_ohm=self.relay_ohm,
            shunt_ohm=self.shunt_ohm,
        )


@dataclass(slots=True)
class FeatureVector:
    """A named, ordered feature vector for one asset at one snapshot."""

    asset_id: str
    as_of: datetime
    values: dict[str, float]
    labels: dict[str, str] = field(default_factory=dict)
    quality: QualityResult | None = None
    twin: TwinResult | None = None

    def array(self, names: list[str] | tuple[str, ...] | None = None) -> np.ndarray:
        keys = list(names) if names is not None else sorted(self.values)
        return np.array([float(self.values.get(key, 0.0)) for key in keys], dtype=float)

    def get(self, key: str, default: float = 0.0) -> float:
        return float(self.values.get(key, default))


MODEL_FEATURES: tuple[str, ...] = (
    "margin_ratio",
    "margin_slope_7d",
    "margin_slope_28d",
    "relay_pct_24h",
    "relay_var_24h",
    "flicker_rate_24h",
    "drop_p50_ms",
    "drop_p95_ms",
    "pickup_p50_ms",
    "step_score_24h",
    "gb_ratio",
    "gb_uncertainty",
    "twin_z",
    "rain_24h",
    "rain_72h",
    "rain_72h_ratio",
    "temp_mean_24h",
    "humidity_mean_24h",
    "neighbour_i_24h",
    "harmonic_mv_24h",
    "feed_min_24h",
    "feed_mean_24h",
    "cable_ir_min_24h",
    "occupancy_rate_24h",
    "axle_mismatch_rate_24h",
    "age_ratio",
    "days_since_repair",
    "repair_count_12m",
    "traffic_per_day",
    "gap_count",
    "stuck_run_max",
    "interpolation_share",
    "finite_ratio",
    "trust_score",
)

FEATURE_LABELS: dict[str, str] = {
    "margin_ratio": "Relay margin vs dry",
    "margin_slope_7d": "7-day relay margin slope",
    "margin_slope_28d": "28-day relay margin slope",
    "relay_pct_24h": "Relay current, 24 h median (% dry)",
    "relay_var_24h": "Relay current variance, 24 h",
    "flicker_rate_24h": "Flicker rate, 24 h",
    "drop_p50_ms": "Drop-away delay p50",
    "drop_p95_ms": "Drop-away delay p95",
    "pickup_p50_ms": "Pick-up delay p50",
    "step_score_24h": "Step-change score, 24 h",
    "gb_ratio": "Effective ballast conductance ratio",
    "gb_uncertainty": "Ballast estimate uncertainty",
    "twin_z": "Twin innovation z-score",
    "rain_24h": "Rain, 24 h",
    "rain_72h": "Rain, 72 h",
    "rain_72h_ratio": "Rain 72 h vs 28-day norm",
    "temp_mean_24h": "Temperature, 24 h",
    "humidity_mean_24h": "Humidity, 24 h",
    "neighbour_i_24h": "Neighbour circuit current",
    "harmonic_mv_24h": "Harmonic / noise floor",
    "feed_min_24h": "Feed voltage minimum, 24 h",
    "feed_mean_24h": "Feed voltage mean, 24 h",
    "cable_ir_min_24h": "Cable insulation minimum, 24 h",
    "occupancy_rate_24h": "Occupancy rate, 24 h",
    "axle_mismatch_rate_24h": "Axle-counter / track-circuit mismatch",
    "age_ratio": "Age vs codal life",
    "days_since_repair": "Days since repair",
    "repair_count_12m": "Repairs in 12 months",
    "traffic_per_day": "Movements per day",
    "gap_count": "Logger gaps",
    "stuck_run_max": "Longest stuck-value run",
    "interpolation_share": "Interpolated sample share",
    "finite_ratio": "Finite sample share",
    "trust_score": "Data trust score",
}


def _window(
    telemetry: AssetTelemetry, key: str, as_of: datetime, hours: float
) -> tuple[np.ndarray, list[datetime]]:
    series = telemetry.signal(key)
    if series is None or not series.observed_at:
        return np.array([]), []
    start = as_of - timedelta(hours=hours)
    lo = bisect_left(series.observed_at, start)
    hi = bisect_right(series.observed_at, as_of)
    if lo >= hi:
        return np.array([]), []
    return np.asarray(series.values[lo:hi], dtype=float), series.observed_at[lo:hi]


def _finite(values: np.ndarray) -> np.ndarray:
    return values[np.isfinite(values)]


def _median(values: np.ndarray, default: float = 0.0) -> float:
    finite = _finite(values)
    return float(np.median(finite)) if finite.size else default


def _sum(values: np.ndarray) -> float:
    finite = _finite(values)
    return float(np.sum(finite)) if finite.size else 0.0


def theil_sen_slope(x: np.ndarray, y: np.ndarray) -> float:
    """Deterministic Theil–Sen slope (median of pairwise slopes)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if x.size < 2:
        return 0.0
    slopes: list[float] = []
    for i in range(x.size - 1):
        dx = x[i + 1 :] - x[i]
        valid = dx != 0
        slopes.extend(((y[i + 1 :] - y[i])[valid] / dx[valid]).tolist())
    return float(np.median(slopes)) if slopes else 0.0


def _daily_series(
    telemetry: AssetTelemetry, key: str, as_of: datetime, days: int, *, free_only: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    series = telemetry.signal(key)
    if series is None or not series.observed_at:
        return np.array([]), np.array([])
    start = as_of - timedelta(days=days)
    lo = bisect_left(series.observed_at, start)
    hi = bisect_right(series.observed_at, as_of)
    if lo >= hi:
        return np.array([]), np.array([])
    occupancy = telemetry.signal("occupancy") if free_only else None
    occ_map: dict[datetime, float] = {}
    if occupancy is not None and occupancy.observed_at:
        occ_lo = bisect_left(occupancy.observed_at, start)
        occ_hi = bisect_right(occupancy.observed_at, as_of)
        occ_map = {
            occupancy.observed_at[idx]: float(occupancy.values[idx])
            for idx in range(occ_lo, occ_hi)
        }
    buckets: dict[int, list[float]] = {}
    for idx in range(lo, hi):
        value = float(series.values[idx])
        if not np.isfinite(value):
            continue
        timestamp = series.observed_at[idx]
        if free_only and occ_map.get(timestamp, 0.0) >= 0.5:
            continue
        bucket = int((timestamp - start).total_seconds() // 86400)
        buckets.setdefault(bucket, []).append(value)
    keys = sorted(buckets)
    if not keys:
        return np.array([]), np.array([])
    x = np.array(keys, dtype=float)
    y = np.array([float(np.median(buckets[key])) for key in keys], dtype=float)
    return x, y


def _flicker_rate(relay_pct: np.ndarray, times: list[datetime], as_of: datetime) -> float:
    if relay_pct.size < 3:
        return 0.0
    diff = np.diff(relay_pct)
    drops = np.sum(np.abs(diff) > 20.0)
    span_days = max(1.0, (as_of - times[0]).total_seconds() / 86400.0) if times else 1.0
    return float(drops / span_days)


def _step_score(daily_y: np.ndarray) -> float:
    if daily_y.size < 2:
        return 0.0
    diff = np.abs(np.diff(daily_y))
    scale = float(np.std(daily_y)) + 1e-6
    return float(np.max(diff) / scale)


def build_features(
    telemetry: AssetTelemetry,
    context: AssetContext,
    as_of: datetime | str,
    *,
    clock_offset_minutes: int = 0,
    supplied_quality: np.ndarray | None = None,
    twin: TwinResult | None = None,
) -> FeatureVector:
    """Build one leakage-safe feature vector at ``as_of``."""
    resolved_as_of = parse_utc(as_of)
    params = context.line_params()
    dry_ma = 1000.0 * dry_current(params)

    relay_7d, relay_times_7d = _window(telemetry, "relay_i", resolved_as_of, 7 * 24)
    occupancy_7d, _ = _window(telemetry, "occupancy", resolved_as_of, 7 * 24)
    free_mask = (
        occupancy_7d < 0.5
        if occupancy_7d.size == relay_7d.size
        else np.ones(relay_7d.size, dtype=bool)
    )
    free_relay = relay_7d[free_mask & np.isfinite(relay_7d)]
    relay_pct = 100.0 * free_relay / dry_ma if dry_ma > 0 else np.array([])
    margin_ratio = float(np.median(relay_pct) / 100.0) if relay_pct.size else 0.0

    _, daily_margin = _daily_series(telemetry, "relay_i", resolved_as_of, 28, free_only=True)
    daily_margin_pct = 100.0 * daily_margin / dry_ma if dry_ma > 0 else np.array([])
    x7 = np.arange(max(0, daily_margin_pct.size - 7), daily_margin_pct.size, dtype=float)
    x28 = np.arange(daily_margin_pct.size, dtype=float)
    slope_7d = theil_sen_slope(x7, daily_margin_pct[-7:]) if daily_margin_pct.size >= 2 else 0.0
    slope_28d = theil_sen_slope(x28, daily_margin_pct) if daily_margin_pct.size >= 2 else 0.0

    relay_24h, _ = _window(telemetry, "relay_i", resolved_as_of, 24)
    occ_24h, _ = _window(telemetry, "occupancy", resolved_as_of, 24)
    free_24h = relay_24h[
        (occ_24h < 0.5 if occ_24h.size == relay_24h.size else np.ones(relay_24h.size, bool))
        & np.isfinite(relay_24h)
    ]
    relay_pct_24h = 100.0 * free_24h / dry_ma if dry_ma > 0 else np.array([])
    relay_var_24h = float(np.var(relay_pct_24h)) if relay_pct_24h.size else 0.0

    drop_7d, _ = _window(telemetry, "drop_ms", resolved_as_of, 7 * 24)
    pickup_7d, _ = _window(telemetry, "pickup_ms", resolved_as_of, 7 * 24)
    drop_finite = _finite(drop_7d)
    pickup_finite = _finite(pickup_7d)
    drop_p50 = float(np.percentile(drop_finite, 50)) if drop_finite.size else 0.0
    drop_p95 = float(np.percentile(drop_finite, 95)) if drop_finite.size else 0.0
    pickup_p50 = float(np.percentile(pickup_finite, 50)) if pickup_finite.size else 0.0

    rain_24h = _sum(_window(telemetry, "rain_mm", resolved_as_of, 24)[0])
    rain_72h = _sum(_window(telemetry, "rain_mm", resolved_as_of, 72)[0])
    rain_28d, _ = _window(telemetry, "rain_mm", resolved_as_of, 28 * 24)
    rain_28d_daily = _daily_series(telemetry, "rain_mm", resolved_as_of, 28)[1]
    rain_norm = _median(rain_28d_daily, 0.0)
    rain_72h_ratio = rain_72h / max(rain_norm * 3.0, 1.0)
    temp_mean = _median(_window(telemetry, "temp_c", resolved_as_of, 24)[0])
    humidity_mean = _median(_window(telemetry, "humidity_pct", resolved_as_of, 24)[0])
    neighbour = _median(_window(telemetry, "neighbour_i", resolved_as_of, 24)[0])
    harmonic = _median(_window(telemetry, "harmonic_mv", resolved_as_of, 24)[0])
    feed_24h, _ = _window(telemetry, "feed_v", resolved_as_of, 24)
    feed_finite = _finite(feed_24h)
    feed_min = float(np.min(feed_finite)) if feed_finite.size else context.feed_v
    feed_mean = float(np.mean(feed_finite)) if feed_finite.size else context.feed_v
    cable_24h, _ = _window(telemetry, "cable_ir", resolved_as_of, 24)
    cable_finite = _finite(cable_24h)
    cable_min = float(np.min(cable_finite)) if cable_finite.size else 800.0
    occupancy_rate = float(np.mean(occ_24h)) if occ_24h.size else 0.0

    axle_24h, _ = _window(telemetry, "axle_occupied", resolved_as_of, 24)
    if axle_24h.size and occ_24h.size == axle_24h.size:
        mismatch = float(np.mean((axle_24h > 0.5) & (occ_24h < 0.5)))
    else:
        mismatch = 0.0

    feed_7d, _ = _window(telemetry, "feed_v", resolved_as_of, 7 * 24)
    feed_aligned = feed_7d if feed_7d.size == relay_7d.size else None
    occ_aligned = (occupancy_7d >= 0.5) if occupancy_7d.size == relay_7d.size else None

    if twin is None:
        twin = run_twin(
            params,
            relay_ma=relay_7d,
            feed_v=feed_aligned,
            occupied=occ_aligned,
            timestamps=[timestamp.timestamp() for timestamp in relay_times_7d],
            dry_ballast_ohm_km=context.dry_ballast_ohm_km,
        )

    quality = assess_quality(
        timestamps=relay_times_7d,
        relay_ma=relay_7d,
        feed_v=feed_aligned,
        as_of=resolved_as_of,
        clock_offset_minutes=clock_offset_minutes,
        supplied_quality=supplied_quality,
    )

    values = {
        "margin_ratio": float(margin_ratio),
        "margin_slope_7d": float(slope_7d),
        "margin_slope_28d": float(slope_28d),
        "relay_pct_24h": _median(relay_pct_24h),
        "relay_var_24h": relay_var_24h,
        "flicker_rate_24h": _flicker_rate(relay_pct, relay_times_7d, resolved_as_of),
        "drop_p50_ms": drop_p50,
        "drop_p95_ms": drop_p95,
        "pickup_p50_ms": pickup_p50,
        "step_score_24h": _step_score(daily_margin_pct),
        "gb_ratio": float(twin.final_gb_ratio) if np.isfinite(twin.final_gb_ratio) else 1.0,
        "gb_uncertainty": float(twin.gb_uncertainty_ohm_km[-1])
        if twin.gb_uncertainty_ohm_km.size
        else 0.0,
        "twin_z": float(twin.final_z),
        "rain_24h": rain_24h,
        "rain_72h": rain_72h,
        "rain_72h_ratio": rain_72h_ratio,
        "temp_mean_24h": temp_mean,
        "humidity_mean_24h": humidity_mean,
        "neighbour_i_24h": neighbour,
        "harmonic_mv_24h": harmonic,
        "feed_min_24h": feed_min,
        "feed_mean_24h": feed_mean,
        "cable_ir_min_24h": cable_min,
        "occupancy_rate_24h": occupancy_rate,
        "axle_mismatch_rate_24h": mismatch,
        "age_ratio": context.age_ratio,
        "days_since_repair": float(context.days_since_repair),
        "repair_count_12m": float(context.repair_count_12m),
        "traffic_per_day": float(context.traffic_per_day),
        "gap_count": float(quality.gap_count),
        "stuck_run_max": float(quality.stuck_run_max),
        "interpolation_share": quality.interpolation_share,
        "finite_ratio": quality.finite_ratio,
        "trust_score": quality.score,
    }
    # NaN/inf must never reach a model or a hash.
    for key, value in list(values.items()):
        if not np.isfinite(value):
            values[key] = 0.0
    return FeatureVector(
        asset_id=context.asset_id,
        as_of=resolved_as_of,
        values=values,
        labels=dict(FEATURE_LABELS),
        quality=quality,
        twin=twin,
    )


def feature_matrix(vectors: list[FeatureVector], names: tuple[str, ...] = MODEL_FEATURES):
    """Stack feature vectors into a deterministic matrix and column order."""
    return (
        np.vstack([vector.array(names) for vector in vectors])
        if vectors
        else np.empty((0, len(names)))
    )


def context_from_asset(asset) -> AssetContext:
    """Build feature context from an AssetSpec or AssetContext-like record (no labels)."""
    return AssetContext(
        asset_id=asset.asset_id,
        station=asset.station,
        division=asset.division,
        route=asset.route,
        length_km=asset.length_km,
        rail_ohm_km=asset.rail_ohm_km,
        dry_ballast_ohm_km=asset.dry_ballast_ohm_km,
        feed_v=asset.feed_v,
        source_ohm=asset.source_ohm,
        relay_ohm=asset.relay_ohm,
        shunt_ohm=asset.shunt_ohm,
        relay_room=asset.relay_room,
        supply_id=asset.supply_id,
        cable_id=asset.cable_id,
        weather_cell=asset.weather_cell,
        age_years=asset.age_years,
        codal_life_years=asset.codal_life_years,
        traffic_per_day=asset.traffic_per_day,
        days_since_repair=120 + int(asset.age_years * 7) % 400,
        repair_count_12m=int(asset.age_years / 6) % 3,
    )
