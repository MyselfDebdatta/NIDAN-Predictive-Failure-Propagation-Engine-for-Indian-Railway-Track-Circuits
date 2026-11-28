"""NIDAN-Bench scenarios (spec §6.2) as canonical, hashable definitions.

Each scenario is a plain dictionary so it can be serialised into the manifest without
numpy or datetime objects. The generator expands it into assets, signals and ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nidan_ai.bench.faults import FaultSpec


@dataclass(frozen=True, slots=True)
class Scenario:
    """Expanded scenario view used by the generator."""

    name: str
    days: int
    asset_count: int
    station_count: int
    event_day: int
    event_mode: str
    faults: tuple[FaultSpec, ...]
    primary_use: str
    weather_intensity: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "days": self.days,
            "asset_count": self.asset_count,
            "station_count": self.station_count,
            "event_day": self.event_day,
            "event_mode": self.event_mode,
            "primary_use": self.primary_use,
            "weather_intensity": self.weather_intensity,
            "faults": [
                {
                    "mode": fault.mode,
                    "start_day": fault.start_day,
                    "end_day": fault.end_day,
                    "severity": fault.severity,
                    "target": fault.target,
                    "shape": fault.shape,
                }
                for fault in self.faults
            ],
        }


_DEFINITIONS: dict[str, dict[str, Any]] = {
    "monsoon-60d": {
        "days": 60,
        "asset_count": 8,
        "station_count": 2,
        "event_day": 59,
        "event_mode": "F1",
        "primary_use": "T1 lead time and the exhibition demonstration",
        "weather_intensity": 1.0,
        "faults": [
            {
                "mode": "F1",
                "start": 0,
                "end": 60,
                "severity": 1.0,
                "target": "all",
                "shape": "linear",
            }
        ],
    },
    "monsoon-fast": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 56,
        "event_mode": "F1",
        "primary_use": "T1 robustness to onset shape",
        "weather_intensity": 1.1,
        "faults": [
            {"mode": "F1", "start": 0, "end": 56, "severity": 1.0, "target": "all", "shape": "exp"}
        ],
    },
    "lightning-cluster": {
        "days": 60,
        "asset_count": 8,
        "station_count": 2,
        "event_day": 40,
        "event_mode": "F7",
        "primary_use": "T3 common-cause clustering",
        "weather_intensity": 1.2,
        "faults": [
            {
                "mode": "F7",
                "start": 40,
                "end": 41,
                "severity": 1.0,
                "target": "cable",
                "shape": "step",
            }
        ],
    },
    "supply-sag": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 35,
        "event_mode": "F6",
        "primary_use": "T3 and T5 correlated supply dips",
        "weather_intensity": 0.7,
        "faults": [
            {
                "mode": "F6",
                "start": 33,
                "end": 37,
                "severity": 1.0,
                "target": "supply",
                "shape": "pulse",
            }
        ],
    },
    "relay-ageing": {
        "days": 180,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 150,
        "event_mode": "F5",
        "primary_use": "T2 and T4 timing drift",
        "weather_intensity": 0.8,
        "faults": [
            {
                "mode": "F5",
                "start": 0,
                "end": 180,
                "severity": 1.0,
                "target": "all",
                "shape": "linear",
            }
        ],
    },
    "points-bridging": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 45,
        "event_mode": "F4",
        "primary_use": "T2 and T5 intermittent partial shunt",
        "weather_intensity": 0.9,
        "faults": [
            {
                "mode": "F4",
                "start": 20,
                "end": 60,
                "severity": 1.0,
                "target": "single",
                "shape": "linear",
            }
        ],
    },
    "cable-ingress": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 50,
        "event_mode": "F8",
        "primary_use": "T2 and T4 cable insulation decline",
        "weather_intensity": 1.0,
        "faults": [
            {
                "mode": "F8",
                "start": 10,
                "end": 60,
                "severity": 1.0,
                "target": "cable",
                "shape": "linear",
            }
        ],
    },
    "masked-decay": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 59,
        "event_mode": "F1",
        "primary_use": "T5 masked decay behind a healthy axle counter",
        "weather_intensity": 1.0,
        "faults": [
            {
                "mode": "F1",
                "start": 0,
                "end": 60,
                "severity": 1.0,
                "target": "all",
                "shape": "linear",
            }
        ],
    },
    "rail-break-step": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 45,
        "event_mode": "F3",
        "primary_use": "T2 hard, rare step change",
        "weather_intensity": 0.6,
        "faults": [
            {
                "mode": "F3",
                "start": 45,
                "end": 46,
                "severity": 1.0,
                "target": "single",
                "shape": "step",
            }
        ],
    },
    "nff-flicker": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 45,
        "event_mode": "F12",
        "primary_use": "T1 flicker feature",
        "weather_intensity": 0.8,
        "faults": [
            {
                "mode": "F12",
                "start": 10,
                "end": 60,
                "severity": 1.0,
                "target": "all",
                "shape": "linear",
            }
        ],
    },
    "traction-noise": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 50,
        "event_mode": "F10",
        "primary_use": "T1 robustness to harmonic rise",
        "weather_intensity": 0.7,
        "faults": [
            {
                "mode": "F10",
                "start": 0,
                "end": 60,
                "severity": 1.0,
                "target": "all",
                "shape": "linear",
            }
        ],
    },
    "config-drift": {
        "days": 60,
        "asset_count": 6,
        "station_count": 1,
        "event_day": 30,
        "event_mode": "F11",
        "primary_use": "T1 advisory after an alteration",
        "weather_intensity": 0.5,
        "faults": [
            {
                "mode": "F11",
                "start": 30,
                "end": 31,
                "severity": 1.0,
                "target": "all",
                "shape": "step",
            }
        ],
    },
}

SCENARIO_NAMES: tuple[str, ...] = tuple(sorted(_DEFINITIONS))
BENCH_SCENARIOS: dict[str, dict[str, Any]] = {name: _DEFINITIONS[name] for name in SCENARIO_NAMES}


def get_scenario(name: str) -> Scenario:
    """Expand a scenario definition into a typed object."""
    if name not in _DEFINITIONS:
        raise KeyError(f"Unknown scenario {name!r}; choose from {SCENARIO_NAMES}")
    definition = _DEFINITIONS[name]
    faults = tuple(
        FaultSpec(
            mode=str(item["mode"]),
            start_day=float(item["start"]),
            end_day=float(item["end"]),
            severity=float(item.get("severity", 1.0)),
            target=str(item.get("target", "all")),
            shape=str(item.get("shape", "linear")),
        )
        for item in definition["faults"]
    )
    return Scenario(
        name=name,
        days=int(definition["days"]),
        asset_count=int(definition["asset_count"]),
        station_count=int(definition["station_count"]),
        event_day=int(definition["event_day"]),
        event_mode=str(definition["event_mode"]),
        faults=faults,
        primary_use=str(definition["primary_use"]),
        weather_intensity=float(definition.get("weather_intensity", 1.0)),
    )


def scenario_manifest() -> dict[str, Any]:
    """Canonical scenario definitions for the bench manifest."""
    return {name: get_scenario(name).as_dict() for name in SCENARIO_NAMES}
