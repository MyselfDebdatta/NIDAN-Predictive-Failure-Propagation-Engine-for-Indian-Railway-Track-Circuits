"""Unscented Kalman filter over the identifiable effective track-circuit state.

State: ``x = [log G_b, log r_eff, log feed_scale]`` where ``G_b`` is effective ballast
conductance (S/km), ``r_eff`` the lumped series term (ohm), and ``feed_scale`` a supply
multiplier. Measurements are relay current (mA) and feed voltage (V).

Identifiability is stated honestly (spec §7.3): with only terminal measurements the
filter recovers **effective** parameters, not a unique physical decomposition. The
covariance is reported with every estimate, and the explainer says "effective".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from nidan_ai.physics.line import LineParams, dry_current, invert_ballast

_LOG_GB_MIN = float(np.log(1.0 / 500.0))
_LOG_GB_MAX = float(np.log(1.0 / 0.05))
_LOG_R_MIN = float(np.log(0.01))
_LOG_R_MAX = float(np.log(10.0))
_LOG_FEED_MIN = float(np.log(0.5))
_LOG_FEED_MAX = float(np.log(1.5))

_N_STATE = 3
_ALPHA = 0.3
_BETA = 2.0
_KAPPA = 0.0
_LAMBDA = _ALPHA * _ALPHA * (_N_STATE + _KAPPA) - _N_STATE
_SCALE = _N_STATE + _LAMBDA
_WM = np.full(2 * _N_STATE + 1, 1.0 / (2.0 * _SCALE))
_WC = _WM.copy()
_WM[0] = _LAMBDA / _SCALE
_WC[0] = _LAMBDA / _SCALE + (1.0 - _ALPHA * _ALPHA + _BETA)
_JITTER = 1e-12 * np.eye(_N_STATE)


@dataclass(slots=True)
class TwinResult:
    """Filtered effective state and diagnostics for one circuit."""

    timestamps: list[float] = field(default_factory=list)
    gb_ohm_km: np.ndarray = field(default_factory=lambda: np.array([]))
    gb_ratio: np.ndarray = field(default_factory=lambda: np.array([]))
    r_eff_ohm: np.ndarray = field(default_factory=lambda: np.array([]))
    feed_scale: np.ndarray = field(default_factory=lambda: np.array([]))
    margin_ratio: np.ndarray = field(default_factory=lambda: np.array([]))
    innovation_ma: np.ndarray = field(default_factory=lambda: np.array([]))
    z_score: np.ndarray = field(default_factory=lambda: np.array([]))
    gb_uncertainty_ohm_km: np.ndarray = field(default_factory=lambda: np.array([]))
    covariance: np.ndarray = field(default_factory=lambda: np.eye(3))
    skipped_updates: int = 0
    missing_samples: int = 0

    @property
    def final_gb_ohm_km(self) -> float:
        return float(self.gb_ohm_km[-1]) if self.gb_ohm_km.size else float("nan")

    @property
    def final_gb_ratio(self) -> float:
        return float(self.gb_ratio[-1]) if self.gb_ratio.size else float("nan")

    @property
    def final_margin_ratio(self) -> float:
        return float(self.margin_ratio[-1]) if self.margin_ratio.size else float("nan")

    @property
    def final_z(self) -> float:
        return float(self.z_score[-1]) if self.z_score.size else 0.0


def _sigma_points(x: np.ndarray, p: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    root = np.linalg.cholesky(_SCALE * (p + _JITTER))
    points = np.empty((7, 3))
    points[0] = x
    points[1:4] = x + root.T
    points[4:7] = x - root.T
    return points, _WM, _WC


def _clip_state(x: np.ndarray) -> np.ndarray:
    return np.array(
        [
            min(max(float(x[0]), _LOG_GB_MIN), _LOG_GB_MAX),
            min(max(float(x[1]), _LOG_R_MIN), _LOG_R_MAX),
            min(max(float(x[2]), _LOG_FEED_MIN), _LOG_FEED_MAX),
        ],
        dtype=float,
    )


def _measurement_relay(x: np.ndarray, params: LineParams) -> float:
    gb = math.exp(float(x[0]))
    r_eff = math.exp(float(x[1]))
    feed_scale = math.exp(float(x[2]))
    rail_ohm_km = r_eff / max(params.length_km, 1e-9)
    gamma = math.sqrt(rail_ohm_km * gb)
    z0 = math.sqrt(rail_ohm_km / gb)
    c = math.cosh(gamma * params.length_km)
    s = math.sinh(gamma * params.length_km)
    b = z0 * s
    cc = s / z0
    load = params.relay_ohm
    z_in = (c * load + b) / (cc * load + c)
    v_in = (params.feed_v * feed_scale) * z_in / (params.source_ohm + z_in)
    v_relay = v_in / (c + b / load)
    return 1000.0 * (v_relay / params.relay_ohm)


def _scalar_update(
    x: np.ndarray,
    p: np.ndarray,
    z: float,
    h,
    *,
    measurement_var: float,
    gate: float,
) -> tuple[np.ndarray, np.ndarray, float, float, bool]:
    points, wm, wc = _sigma_points(x, p)
    hz = np.array([h(point) for point in points])
    z_pred = float(np.sum(wm * hz))
    dx = points - x
    dz = hz - z_pred
    s = float(np.sum(wc * dz * dz) + measurement_var)
    if not np.isfinite(s) or s <= 0:
        return x, p, 0.0, 0.0, False
    cross = np.zeros_like(x)
    for i in range(points.shape[0]):
        cross += wc[i] * dx[i] * dz[i]
    innovation = z - z_pred
    z_score = innovation / np.sqrt(s)
    if abs(z_score) > gate:
        # Robust gating: a single implausible sample must not move the state.
        return x, p, innovation, z_score, False
    k = cross / s
    x_new = _clip_state(x + k * innovation)
    p_new = p - np.outer(k, cross)
    p_new = 0.5 * (p_new + p_new.T)
    return x_new, p_new, innovation, z_score, True


def run_twin(
    params: LineParams,
    *,
    relay_ma: np.ndarray | list[float],
    feed_v: np.ndarray | list[float] | None = None,
    occupied: np.ndarray | list[bool] | None = None,
    timestamps: np.ndarray | list[float] | None = None,
    dry_ballast_ohm_km: float = 8.0,
    relay_sigma_ma: float | None = None,
    feed_sigma_v: float = 0.08,
    gate: float = 3.5,
) -> TwinResult:
    """Run the UKF deterministically over one circuit's terminal measurements.

    ``relay_ma`` may contain ``NaN`` for missing samples. No random initialisation is used.
    """
    relay = np.asarray(relay_ma, dtype=float).ravel()
    if timestamps is None:
        ts = np.arange(relay.size, dtype=float)
    else:
        ts = np.asarray(timestamps, dtype=float).ravel()
        if ts.size != relay.size:
            raise ValueError("timestamps and relay_ma must have the same length")
    feeds = None if feed_v is None else np.asarray(feed_v, dtype=float).ravel()
    if feeds is not None and feeds.size != relay.size:
        raise ValueError("feed_v and relay_ma must have the same length")
    occ = None if occupied is None else np.asarray(occupied, dtype=bool).ravel()
    if occ is not None and occ.size != relay.size:
        raise ValueError("occupied and relay_ma must have the same length")
    if relay.size == 0:
        return TwinResult()

    dry_ma = 1000.0 * dry_current(params)
    sigma = relay_sigma_ma if relay_sigma_ma is not None else max(1.0, 0.01 * dry_ma)

    x = np.array(
        [
            np.log(1.0 / max(dry_ballast_ohm_km, 1e-6)),
            np.log(max(params.rail_ohm_km * params.length_km, 1e-6)),
            0.0,
        ],
        dtype=float,
    )
    p = np.diag([0.35**2, 0.20**2, 0.05**2])
    q_step = np.diag([0.025**2, 0.004**2, 0.002**2])

    gb_series = np.full(relay.size, np.nan)
    ratio_series = np.full(relay.size, np.nan)
    r_series = np.full(relay.size, np.nan)
    feed_series = np.full(relay.size, np.nan)
    margin_series = np.full(relay.size, np.nan)
    innovation_series = np.full(relay.size, np.nan)
    z_series = np.full(relay.size, np.nan)
    gb_unc_series = np.full(relay.size, np.nan)
    skipped = 0
    missing = 0

    for i in range(relay.size):
        # Predict: random-walk state with process noise.
        p = p + q_step
        x = _clip_state(x)

        observed = relay[i]
        is_occupied = bool(occ[i]) if occ is not None else False
        if np.isfinite(observed) and observed > 0 and not is_occupied:
            x, p, innovation, z, accepted = _scalar_update(
                x,
                p,
                observed,
                lambda point: _measurement_relay(point, params),
                measurement_var=sigma * sigma,
                gate=gate,
            )
            innovation_series[i] = innovation
            z_series[i] = z
            if not accepted:
                skipped += 1
        elif not is_occupied:
            missing += 1

        if feeds is not None and np.isfinite(feeds[i]) and feeds[i] > 0:
            x, p, _, _, accepted = _scalar_update(
                x,
                p,
                float(feeds[i]),
                lambda point: params.feed_v * float(np.exp(point[2])),
                measurement_var=feed_sigma_v * feed_sigma_v,
                gate=gate,
            )
            if not accepted:
                skipped += 1

        gb = float(np.exp(x[0]))
        gb_series[i] = 1.0 / gb
        ratio_series[i] = gb * dry_ballast_ohm_km
        r_series[i] = float(np.exp(x[1]))
        feed_series[i] = float(np.exp(x[2]))
        margin_series[i] = (
            observed / dry_ma if np.isfinite(observed) and dry_ma > 0 else float("nan")
        )
        # Delta method: sd(G_b) ~= G_b * sd(log G_b).
        gb_unc_series[i] = gb * float(np.sqrt(max(p[0, 0], 0.0)))

    return TwinResult(
        timestamps=[float(value) for value in ts],
        gb_ohm_km=gb_series,
        gb_ratio=ratio_series,
        r_eff_ohm=r_series,
        feed_scale=feed_series,
        margin_ratio=margin_series,
        innovation_ma=innovation_series,
        z_score=z_series,
        gb_uncertainty_ohm_km=gb_unc_series,
        covariance=p,
        skipped_updates=skipped,
        missing_samples=missing,
    )


def estimate_snapshot(
    params: LineParams,
    relay_ma: float,
    *,
    dry_ballast_ohm_km: float = 8.0,
    relative_measurement_sigma: float = 0.02,
) -> dict[str, float]:
    """Deterministic single-snapshot inverse estimate (the documented 10.4% check)."""
    dry_ma = 1000.0 * dry_current(params)
    pct = 100.0 * relay_ma / dry_ma if dry_ma > 0 else 0.0
    rb, uncertainty = invert_ballast_with_uncertainty(
        pct, params, relative_measurement_sigma=relative_measurement_sigma
    )
    return {
        "relay_pct_of_dry": pct,
        "ballast_ohm_km": rb,
        "ballast_uncertainty_ohm_km": uncertainty,
        "gb_ratio": dry_ballast_ohm_km / rb if rb > 0 else 0.0,
        "margin_ratio": pct / 100.0,
    }


def invert_ballast_with_uncertainty(
    percent_of_dry: float,
    params: LineParams,
    *,
    relative_measurement_sigma: float = 0.02,
) -> tuple[float, float]:
    """Effective ballast resistance plus a first-order uncertainty."""
    estimate = invert_ballast(percent_of_dry, params)
    plus = invert_ballast(percent_of_dry + 100.0 * relative_measurement_sigma, params)
    return estimate, float(abs(plus - estimate))
