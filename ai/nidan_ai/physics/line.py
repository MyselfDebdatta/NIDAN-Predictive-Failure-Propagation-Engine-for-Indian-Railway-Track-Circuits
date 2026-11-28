"""Uniform lossy transmission-line model of a DC track circuit.

The model follows the documented illustration (research dossier §5.3, Appendix C):
series rail resistance ``r`` (ohm/km), shunt ballast conductance ``g = 1/R_b`` (S/km),
source at ``x = 0`` through a source resistance, relay at ``x = L``. The ABCD matrix of
the line gives the relay current. Parameters are illustrative and are **not** calibrated
to any Indian Railways circuit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class LineParams:
    """Physical design parameters of one track circuit."""

    length_km: float = 0.75
    rail_ohm_km: float = 0.10
    feed_v: float = 12.0
    source_ohm: float = 3.0
    relay_ohm: float = 9.0
    shunt_ohm: float = 0.5

    def with_factors(
        self,
        *,
        rail_factor: float = 1.0,
        feed_factor: float = 1.0,
        relay_factor: float = 1.0,
    ) -> LineParams:
        """Return a copy with multiplicative degradation factors applied."""
        return LineParams(
            length_km=self.length_km,
            rail_ohm_km=self.rail_ohm_km * rail_factor,
            feed_v=self.feed_v * feed_factor,
            source_ohm=self.source_ohm,
            relay_ohm=self.relay_ohm * relay_factor,
            shunt_ohm=self.shunt_ohm,
        )


def _abcd(g: float, params: LineParams) -> tuple[float, float, float, float]:
    gamma = math.sqrt(params.rail_ohm_km * g)
    z0 = math.sqrt(params.rail_ohm_km / g)
    c = math.cosh(gamma * params.length_km)
    s = math.sinh(gamma * params.length_km)
    return c, z0 * s, s / z0, c


def relay_current(
    params: LineParams,
    ballast_ohm_km: float | None,
    *,
    occupied: bool = False,
    feed_scale: float = 1.0,
) -> float:
    """Relay current in amperes.

    ``ballast_ohm_km=None`` means a perfectly dry circuit (no shunt leakage), which is the
    analytic series case used by the dry-case test. ``occupied=True`` places the train shunt
    across the relay end.
    """
    load = (
        params.relay_ohm * params.shunt_ohm / (params.relay_ohm + params.shunt_ohm)
        if occupied
        else params.relay_ohm
    )
    feed = params.feed_v * feed_scale
    if ballast_ohm_km is None:
        return (
            feed
            / (params.source_ohm + params.rail_ohm_km * params.length_km + load)
            * (load / params.relay_ohm)
        )
    if ballast_ohm_km <= 0:
        return 0.0
    g = 1.0 / ballast_ohm_km
    a, b, c, d = _abcd(g, params)
    z_in = (a * load + b) / (c * load + d)
    v_in = feed * z_in / (params.source_ohm + z_in)
    v_relay = v_in / (a + b / load)
    return float(v_relay / params.relay_ohm)


def dry_current(params: LineParams) -> float:
    """Relay current of the same circuit with no ballast leakage."""
    return relay_current(params, None)


def relay_percent_of_dry(
    params: LineParams,
    ballast_ohm_km: float | None,
    *,
    occupied: bool = False,
) -> float:
    """Relay current as a percentage of the dry-circuit current."""
    return 100.0 * relay_current(params, ballast_ohm_km, occupied=occupied) / dry_current(params)


def relay_margin_ratio(params: LineParams, ballast_ohm_km: float | None) -> float:
    """Relay current relative to dry (1.0 = dry, 0.0 = no current)."""
    return relay_current(params, ballast_ohm_km) / dry_current(params)


def effective_gb_ratio(params: LineParams, ballast_ohm_km: float | None) -> float:
    """Effective ballast conductance relative to the dry design baseline.

    The baseline is the design ``dry_ballast_ohm_km`` encoded by the caller; here we report
    conductance itself so the twin can divide by its own prior.
    """
    if ballast_ohm_km is None:
        return 0.0
    return 1.0 / ballast_ohm_km


def voltage_current_profile(
    params: LineParams,
    ballast_ohm_km: float | None,
    *,
    points: int = 11,
    occupied: bool = False,
    feed_scale: float = 1.0,
) -> dict[str, np.ndarray]:
    """Voltage and current along the line from the feed end (x=0) to the relay end (x=L)."""
    load = (
        params.relay_ohm * params.shunt_ohm / (params.relay_ohm + params.shunt_ohm)
        if occupied
        else params.relay_ohm
    )
    feed = params.feed_v * feed_scale
    if ballast_ohm_km is None or ballast_ohm_km <= 0:
        z_in = params.rail_ohm_km * params.length_km + load
        v_in = feed * z_in / (params.source_ohm + z_in)
        i_in = (feed - v_in) / params.source_ohm
        x = np.linspace(0.0, params.length_km, points)
        v = v_in - i_in * params.rail_ohm_km * x
        i = np.full_like(v, i_in)
        return {"x_km": x, "voltage_v": v, "current_a": i}

    g = 1.0 / ballast_ohm_km
    a, b, c, d = _abcd(g, params)
    z_in = (a * load + b) / (c * load + d)
    v_in = feed * z_in / (params.source_ohm + z_in)
    i_in = (feed - v_in) / params.source_ohm
    gamma = np.sqrt(params.rail_ohm_km * g)
    z0 = np.sqrt(params.rail_ohm_km / g)
    x = np.linspace(0.0, params.length_km, points)
    v = v_in * np.cosh(gamma * x) - i_in * z0 * np.sinh(gamma * x)
    i = i_in * np.cosh(gamma * x) - (v_in / z0) * np.sinh(gamma * x)
    return {"x_km": x, "voltage_v": v, "current_a": i}


def invert_ballast(
    percent_of_dry: float,
    params: LineParams,
    *,
    lo: float = 0.05,
    hi: float = 500.0,
    iterations: int = 80,
) -> float:
    """Invert the twin: effective ballast resistance (ohm-km) from relay current % of dry.

    ``relay_percent_of_dry`` is monotone increasing in ``R_b``, so geometric bisection is
    safe and deterministic. This recovers an *effective* parameter, not a physical soil
    property (spec §7.3).
    """
    target = float(percent_of_dry)
    for _ in range(iterations):
        mid = float(np.sqrt(lo * hi))
        if relay_percent_of_dry(params, mid) < target:
            lo = mid
        else:
            hi = mid
    return float(np.sqrt(lo * hi))


def invert_ballast_with_uncertainty(
    percent_of_dry: float,
    params: LineParams,
    *,
    relative_measurement_sigma: float = 0.02,
) -> tuple[float, float]:
    """Effective ballast resistance and a first-order uncertainty (ohm-km)."""
    estimate = invert_ballast(percent_of_dry, params)
    delta = abs(
        invert_ballast(percent_of_dry + 100.0 * relative_measurement_sigma, params) - estimate
    )
    return estimate, float(delta)
