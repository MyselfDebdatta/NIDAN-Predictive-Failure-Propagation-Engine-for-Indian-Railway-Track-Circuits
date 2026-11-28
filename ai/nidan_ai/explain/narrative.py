"""Templated, deterministic explanation text with a mandatory falsifier.

No LLM and no free generation: every sentence is filled from a computed field. The physics
lens reports effective quantities (never over-claiming a physical decomposition); the model
lens reports signed SHAP contributions, the conformal set and its measured coverage; the
precedent lens is built separately from real rows.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nidan_ai.data.features import FeatureVector
from nidan_ai.physics.twin import TwinResult

_FALSIFIERS: dict[str, str] = {
    "F1": (
        "If a repeat 0.5 ohm shunt test holds relay current above 75% of dry for five "
        "movements, the effective-ballast explanation is wrong and the cause is not F1."
    ),
    "F3": (
        "If rail-bond resistance and relay current are stable across the next three block "
        "inspections, the step is a measurement artefact, not F3."
    ),
    "F5": (
        "If drop-away is under 0.5 s on the next five movements, the pattern is a logger "
        "timing artefact, not F5 relay ageing."
    ),
    "F6": (
        "If feed voltage returns to its 30-day median while relay current stays low, the cause "
        "is not F6 supply."
    ),
    "F12": (
        "If the flickers disappear when the logger clock is corrected, the pattern is a data "
        "artefact, not F12."
    ),
}
_DEFAULT_FALSIFIER = (
    "If the next 24 h of telemetry returns relay margin and effective ballast conductance to "
    "their dry baseline, this explanation is falsified."
)


@dataclass(slots=True)
class PhysicsNarrative:
    headline: str
    state: list[dict[str, str]]
    falsifier: str


def _fmt(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def physics_narrative(
    vector: FeatureVector,
    twin: TwinResult | None,
    *,
    mode: str,
    rain_norm_72h: float = 22.0,
    days_window: int = 7,
) -> PhysicsNarrative:
    """Build the physics lens from computed twin and feature values."""
    gb_ratio = vector.get("gb_ratio", 1.0)
    margin = vector.get("margin_ratio", 0.0)
    rain_72h = vector.get("rain_72h")
    slope = vector.get("margin_slope_7d")
    drop_p95 = vector.get("drop_p95_ms")
    delta_pct = (gb_ratio - 1.0) * 100.0
    direction = "+" if delta_pct >= 0 else ""
    headline = (
        f"Effective ballast conductance {direction}{_fmt(delta_pct)}% versus the dry design "
        f"baseline; relay margin {_fmt(100.0 * margin)}% of dry. "
        f"Rain {_fmt(rain_72h)} mm in 72 h vs {_fmt(rain_norm_72h)} mm median."
    )
    state = [
        {
            "label": "Effective ballast conductance",
            "value": f"{_fmt(gb_ratio, 2)}x dry",
            "baseline": "1.00x dry",
        },
        {
            "label": "Relay margin",
            "value": f"{_fmt(100.0 * margin)}% of dry",
            "baseline": "100% of dry",
        },
        {
            "label": "Rain, 72 h",
            "value": f"{_fmt(rain_72h)} mm",
            "baseline": f"{_fmt(rain_norm_72h)} mm median",
        },
        {
            "label": "Relay drop-away p95",
            "value": f"{_fmt(drop_p95, 0)} ms",
            "baseline": "250 ms design",
        },
    ]
    if slope < -0.05:
        state[1]["value"] += f" ({_fmt(slope, 2)} pp/day)"
    return PhysicsNarrative(
        headline=headline,
        state=state[:4],
        falsifier=_FALSIFIERS.get(mode, _DEFAULT_FALSIFIER),
    )


def agreement(
    *,
    physics_driver: str,
    shap_top: list[dict[str, float | str]],
    mode_set: list[str],
    trust_score: float,
) -> str:
    """Rule from spec §9.4: high, medium or low, never hidden."""
    if not shap_top:
        return "low"
    top_feature = str(shap_top[0]["feature"])
    top_value = float(shap_top[0]["value"])
    same_direction = (
        physics_driver in {"margin_ratio", "gb_ratio"}
        and top_feature in {"margin_ratio", "gb_ratio"}
    ) or (physics_driver == top_feature)
    if trust_score < 0.6:
        return "low"
    if same_direction and len(mode_set) == 1 and abs(top_value) > 0.02:
        return "high"
    if same_direction:
        return "medium"
    return "low"


def calibration_note(coverage: float, held_out_n: int, *, capped: bool = False) -> str:
    """Templated calibration note; never claims a target it did not measure."""
    note = (
        f"Conformal set coverage {coverage:.3f} on {held_out_n} held-out outcomes; "
        "calibration is per division and horizon."
    )
    if capped:
        note += " Set capped at three modes; reported coverage is the capped-set value."
    return note


def model_narrative(
    *,
    shap_top: list[dict[str, float | str]],
    mode_set: list[str],
    coverage: float,
    held_out_n: int,
    agreement_level: str,
    capped: bool = False,
) -> dict[str, object]:
    """Build the model lens fields for the backend ``ModelExplanation`` model."""
    return {
        "shapTop": shap_top,
        "calibrationNote": calibration_note(coverage, held_out_n, capped=capped),
        "modeSet": mode_set,
        "modeSetCoverage": float(np.clip(coverage, 0.0, 1.0)),
        "agreement": agreement_level,
    }
