"""F1–F12 fault injectors for NIDAN-Bench.

The taxonomy is exactly the one in the research dossier §3.4 and spec Appendix B. No new
failure mode is introduced. Each injector maps a ground-truth fault to observable signal
changes; the label is stored separately so it can never leak into a feature.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nidan_ai.config import FAILURE_MODES

# Modes exercised by the first release and the bench scenarios that carry them.
BENCH_MODES = ("F1", "F3", "F4", "F5", "F6", "F7", "F8", "F10", "F11", "F12")


@dataclass(frozen=True, slots=True)
class FaultSpec:
    """One injected fault with a ground-truth onset and severity."""

    mode: str
    start_day: float
    end_day: float
    severity: float = 1.0
    target: str = "all"  # all | cable | supply | single | weather
    shape: str = "linear"  # linear | exp | step | pulse

    def __post_init__(self) -> None:
        if self.mode not in FAILURE_MODES:
            raise ValueError(f"Unknown failure mode {self.mode!r}")
        if self.end_day < self.start_day:
            raise ValueError("end_day must be >= start_day")

    def progress(self, day: float) -> float:
        """Fractional progress of the fault at ``day`` in [0, 1]."""
        if day <= self.start_day:
            return 0.0
        if self.shape == "step":
            return 1.0 if day >= self.start_day else 0.0
        if self.shape == "pulse":
            return 1.0 if self.start_day <= day <= self.end_day else 0.0
        span = max(self.end_day - self.start_day, 1e-9)
        frac = min(max((day - self.start_day) / span, 0.0), 1.0)
        if self.shape == "exp":
            return float((np.exp(3.0 * frac) - 1.0) / (np.exp(3.0) - 1.0))
        return float(frac)


def ballast_resistance_factor(
    specs: list[FaultSpec], day: float, dry_ballast_ohm_km: float
) -> float:
    """Multiplier on dry ballast resistance from F1 (and F7 as an effective step)."""
    factor = 1.0
    for spec in specs:
        if spec.mode == "F1":
            progress = spec.progress(day)
            target = max(1.2, dry_ballast_ohm_km * (1.0 - 0.82 * spec.severity))
            factor = min(factor, 1.0 - progress * (1.0 - target / dry_ballast_ohm_km))
        elif spec.mode == "F7":
            # A surge degrades a shared cable route; the effective leakage rises in a step.
            if day >= spec.start_day:
                factor = min(factor, max(0.35, 1.0 - 0.35 * spec.severity))
    return float(max(0.05, factor))


def rail_resistance_factor(specs: list[FaultSpec], day: float) -> float:
    """Multiplier on the series rail/bond term from F3."""
    factor = 1.0
    for spec in specs:
        if spec.mode == "F3" and day >= spec.start_day:
            factor = max(factor, 1.0 + 1.5 * spec.severity)
    return float(factor)


def feed_voltage_factor(specs: list[FaultSpec], day: float) -> float:
    """Multiplier on feed voltage from F6."""
    factor = 1.0
    for spec in specs:
        if spec.mode == "F6":
            progress = spec.progress(day)
            if progress > 0:
                factor = min(factor, 1.0 - 0.28 * spec.severity * progress)
    return float(factor)


def timing_extra_ms(specs: list[FaultSpec], day: float) -> float:
    """Extra relay drop-away delay from F5 (relay ageing)."""
    extra = 0.0
    for spec in specs:
        if spec.mode == "F5":
            extra += 450.0 * spec.severity * spec.progress(day)
        if spec.mode == "F9":
            extra += 250.0 * spec.severity * spec.progress(day)
    return float(extra)


def harmonic_multiplier(specs: list[FaultSpec], day: float) -> float:
    """Noise-floor multiplier from F10 and F7."""
    factor = 1.0
    for spec in specs:
        if spec.mode == "F10":
            factor += 4.0 * spec.severity * spec.progress(day)
        if spec.mode == "F7" and spec.start_day <= day <= spec.start_day + 0.5:
            factor += 8.0 * spec.severity
    return float(factor)


def cable_insulation_factor(specs: list[FaultSpec], day: float) -> float:
    """Multiplier on cable insulation resistance from F8."""
    factor = 1.0
    for spec in specs:
        if spec.mode == "F8":
            factor = min(factor, max(0.05, 1.0 - 0.85 * spec.severity * spec.progress(day)))
    return float(factor)


def flicker_probability(specs: list[FaultSpec], day: float, base: float = 0.002) -> float:
    """Per-sample probability of a short unexplained flicker (F12)."""
    probability = base
    for spec in specs:
        if spec.mode == "F12":
            probability += 0.08 * spec.severity * spec.progress(day)
        if spec.mode == "F2":
            probability += 0.03 * spec.severity * spec.progress(day)
    return float(min(0.35, probability))


def neighbour_leakage_factor(specs: list[FaultSpec], day: float) -> float:
    """Multiplier on neighbour current from F2 (insulated joint failure)."""
    factor = 1.0
    for spec in specs:
        if spec.mode == "F2":
            factor += 0.9 * spec.severity * spec.progress(day)
    return float(factor)


def partial_shunt_probability(specs: list[FaultSpec], day: float) -> float:
    """Probability of a persistent partial shunt at points (F4)."""
    probability = 0.0
    for spec in specs:
        if spec.mode == "F4":
            probability += 0.10 * spec.severity * spec.progress(day)
    return float(min(0.5, probability))


def reset_spike(specs: list[FaultSpec], day: float) -> bool:
    """True when an F11 configuration/reset event is active."""
    return any(spec.mode == "F11" and abs(day - spec.start_day) <= 0.5 for spec in specs)
