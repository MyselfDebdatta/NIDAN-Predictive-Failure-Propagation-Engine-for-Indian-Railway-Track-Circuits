"""Domain-randomised NIDAN-Bench stream generator.

The generator drives the transmission-line twin with synthetic weather, traffic and
maintenance calendars, injects F1–F12 faults, and records the hidden state and event time
as ground truth. Noise, logger gaps, stuck values, clock skew and quantisation are injected
into the *data*, not the label, so models learn robustness rather than a clean simulation.

Every scenario takes a seed. Identical seed + version produces byte-identical output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

from nidan_ai.bench import faults as fault_mod
from nidan_ai.bench.faults import FaultSpec
from nidan_ai.bench.manifest import BenchManifest, build_manifest, stable_id
from nidan_ai.bench.scenarios import Scenario, get_scenario, scenario_manifest
from nidan_ai.config import BENCH_VERSION, SIGNAL_KEYS
from nidan_ai.physics.line import LineParams, relay_current

_STATIONS = (
    ("ADRA", "ADRA", "Up Main"),
    ("BKSC", "BKSC", "Down Main"),
    ("KUR", "KUR", "Up Goods"),
    ("TATA", "TATA", "Down Goods"),
    ("ROU", "ROU", "Up Main"),
    ("JSG", "JSG", "Down Main"),
)
_WEATHER_CELLS = (
    "wx-20.30N-85.83E",
    "wx-22.33N-87.32E",
    "wx-22.80N-86.20E",
    "wx-23.24N-87.07E",
)


@dataclass(frozen=True, slots=True)
class AssetSpec:
    """One bench track circuit with design data and ground truth."""

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
    faulted: bool
    event_day: int | None
    event_mode: str | None
    installed: str = "2012-04-01"

    def line_params(self) -> LineParams:
        return LineParams(
            length_km=self.length_km,
            rail_ohm_km=self.rail_ohm_km,
            feed_v=self.feed_v,
            source_ohm=self.source_ohm,
            relay_ohm=self.relay_ohm,
            shunt_ohm=self.shunt_ohm,
        )


@dataclass(frozen=True, slots=True)
class BenchEvent:
    """Ground-truth failure/confirmed event used for labels and precedents."""

    asset_id: str
    mode: str
    event_day: int
    event_time: str
    smms_id: str
    outcome: str
    confirmed_mode: str
    station: str
    division: str
    confirmed: bool = True


@dataclass(slots=True)
class BenchStream:
    """A generated scenario: assets, hourly signals, ground truth and manifest."""

    scenario: str
    seed: int
    division: str
    assets: list[AssetSpec]
    timestamps: list[datetime]
    series: dict[str, dict[str, np.ndarray]]
    events: list[BenchEvent]
    manifest: BenchManifest
    scenario_def: Scenario
    clock_offsets_minutes: dict[str, int] = field(default_factory=dict)
    quality_injections: dict[str, list[str]] = field(default_factory=dict)

    @property
    def asset_ids(self) -> list[str]:
        return [asset.asset_id for asset in self.assets]

    def by_id(self, asset_id: str) -> AssetSpec:
        for asset in self.assets:
            if asset.asset_id == asset_id:
                return asset
        raise KeyError(asset_id)

    def event_for(self, asset_id: str) -> BenchEvent | None:
        for event in self.events:
            if event.asset_id == asset_id:
                return event
        return None


def _make_assets(scenario: Scenario, seed: int, division: str | None) -> list[AssetSpec]:
    rng = np.random.default_rng(seed * 1009 + 17)
    stations = _STATIONS[: max(1, scenario.station_count)]
    assets: list[AssetSpec] = []
    for index in range(scenario.asset_count):
        station, station_division, route = stations[index % len(stations)]
        per_station_index = index // len(stations)
        chosen_division = division or station_division
        weather_cell = _WEATHER_CELLS[(index % len(stations)) % len(_WEATHER_CELLS)]
        relay_room = f"{station}/RR/{1 + per_station_index % 2}"
        supply_id = f"{station}/IPS/{1 + per_station_index % 2}"
        cable_id = f"{station}/CBL/{1 + per_station_index % 2}"
        length = float(rng.uniform(0.30, 1.50))
        rail = float(rng.uniform(0.05, 0.20))
        dry_ballast = float(rng.uniform(4.0, 20.0))
        feed = float(rng.uniform(9.0, 14.0))
        source = float(rng.uniform(2.0, 5.0))
        relay = float(rng.uniform(4.0, 12.0))
        shunt = float(rng.uniform(0.30, 0.80))
        age = float(rng.uniform(1.0, 25.0))
        codal = int(rng.integers(15, 31))
        traffic = int(rng.integers(10, 121))
        assets.append(
            AssetSpec(
                asset_id=f"{station}/TC/{index + 1:02d}T",
                station=station,
                division=chosen_division,
                route=route,
                length_km=length,
                rail_ohm_km=rail,
                dry_ballast_ohm_km=dry_ballast,
                feed_v=feed,
                source_ohm=source,
                relay_ohm=relay,
                shunt_ohm=shunt,
                relay_room=relay_room,
                supply_id=supply_id,
                cable_id=cable_id,
                weather_cell=weather_cell,
                age_years=age,
                codal_life_years=codal,
                traffic_per_day=traffic,
                faulted=False,
                event_day=None,
                event_mode=None,
            )
        )

    # Choose the shared group targeted by cable/supply/weather faults, deterministically.
    target = scenario.faults[0].target if scenario.faults else "all"
    if target == "cable":
        counts: dict[str, int] = {}
        for asset in assets:
            counts[asset.cable_id] = counts.get(asset.cable_id, 0) + 1
        chosen = sorted(counts, key=lambda key: (-counts[key], key))[0]
        selected = {asset.asset_id for asset in assets if asset.cable_id == chosen}
    elif target == "supply":
        counts = {}
        for asset in assets:
            counts[asset.supply_id] = counts.get(asset.supply_id, 0) + 1
        chosen = sorted(counts, key=lambda key: (-counts[key], key))[0]
        selected = {asset.asset_id for asset in assets if asset.supply_id == chosen}
    elif target == "weather":
        selected = {
            asset.asset_id for asset in assets if asset.weather_cell == assets[0].weather_cell
        }
    elif target == "single":
        selected = {assets[0].asset_id}
    else:
        # "all": most assets faulted, but keep two censored/healthy controls per scenario.
        keep_healthy = 2 if len(assets) > 3 else 0
        selected = {asset.asset_id for asset in assets[: len(assets) - keep_healthy]}

    jitter_rng = np.random.default_rng(seed * 7919 + 3)
    result: list[AssetSpec] = []
    for asset in assets:
        faulted = asset.asset_id in selected
        if faulted:
            jitter = (
                0
                if scenario.name in {"monsoon-60d", "masked-decay"}
                else int(jitter_rng.integers(-1, 2))
            )
            event_day = max(1, min(scenario.days - 1, scenario.event_day + jitter))
            event_mode = scenario.event_mode
        else:
            event_day = None
            event_mode = None
        result.append(
            AssetSpec(
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
                faulted=faulted,
                event_day=event_day,
                event_mode=event_mode,
            )
        )
    return result


def _active_faults(asset: AssetSpec, scenario: Scenario) -> list[FaultSpec]:
    if not asset.faulted:
        return []
    return list(scenario.faults)


def _weather(
    scenario: Scenario, seed: int, stations: list[str], hours: int
) -> dict[str, dict[str, np.ndarray]]:
    day = np.arange(hours) / 24.0
    weather: dict[str, dict[str, np.ndarray]] = {}
    for station_index, station in enumerate(stations):
        local = np.random.default_rng(seed * 31337 + 5 + station_index)
        base = local.gamma(0.55, 1.4 * scenario.weather_intensity, hours)
        # A monsoon burst around the event window makes 72 h rain meaningful.
        burst = np.exp(-0.5 * ((day - scenario.event_day * 0.6) / 6.0) ** 2)
        rain = base + 2.2 * scenario.weather_intensity * burst * (local.random(hours) < 0.35)
        rain = np.maximum(rain, 0.0)
        seasonal = 27.0 + 5.0 * np.sin(2.0 * np.pi * (day - 100.0) / 365.0)
        diurnal = 4.0 * np.sin(2.0 * np.pi * (np.arange(hours) % 24) / 24.0)
        temp = seasonal + diurnal + local.normal(0.0, 0.8, hours)
        humidity = np.clip(
            55.0 + 12.0 * (rain > 0.1) + 8.0 * burst + local.normal(0, 4, hours), 20, 100
        )
        weather[station] = {"rain_mm": rain, "temp_c": temp, "humidity_pct": humidity}
    return weather


def generate(
    scenario_name: str = "monsoon-60d",
    *,
    seed: int = 42,
    division: str | None = None,
    days: int | None = None,
) -> BenchStream:
    """Generate one scenario deterministically."""
    scenario = get_scenario(scenario_name)
    if days is not None:
        scenario = Scenario(
            name=scenario.name,
            days=int(days),
            asset_count=scenario.asset_count,
            station_count=scenario.station_count,
            event_day=min(scenario.event_day, int(days) - 1),
            event_mode=scenario.event_mode,
            faults=scenario.faults,
            primary_use=scenario.primary_use,
            weather_intensity=scenario.weather_intensity,
        )
    assets = _make_assets(scenario, seed, division)
    hours = scenario.days * 24 + 1
    start = datetime(2026, 6, 1, tzinfo=UTC)
    timestamps = [start + timedelta(hours=index) for index in range(hours)]
    day_axis = np.arange(hours) / 24.0
    stations = sorted({asset.station for asset in assets})
    weather = _weather(scenario, seed, stations, hours)

    series: dict[str, dict[str, np.ndarray]] = {}
    clock_offsets: dict[str, int] = {}
    quality_injections: dict[str, list[str]] = {}

    for asset_index, asset in enumerate(assets):
        local = np.random.default_rng(seed * 104729 + asset_index * 37 + 11)
        params = asset.line_params()
        station_weather = weather[asset.station]
        rain = station_weather["rain_mm"]
        temp = station_weather["temp_c"]
        humidity = station_weather["humidity_pct"]

        active = _active_faults(asset, scenario)
        ballast_factor = np.array(
            [
                fault_mod.ballast_resistance_factor(active, day, asset.dry_ballast_ohm_km)
                for day in day_axis
            ]
        )
        rail_factor = np.array([fault_mod.rail_resistance_factor(active, day) for day in day_axis])
        feed_factor = np.array([fault_mod.feed_voltage_factor(active, day) for day in day_axis])
        timing_extra = np.array([fault_mod.timing_extra_ms(active, day) for day in day_axis])
        harmonic = np.array([fault_mod.harmonic_multiplier(active, day) for day in day_axis])
        cable_factor = np.array(
            [fault_mod.cable_insulation_factor(active, day) for day in day_axis]
        )
        neighbour_factor = np.array(
            [fault_mod.neighbour_leakage_factor(active, day) for day in day_axis]
        )
        flicker_prob = np.array([fault_mod.flicker_probability(active, day) for day in day_axis])
        partial_prob = np.array(
            [fault_mod.partial_shunt_probability(active, day) for day in day_axis]
        )

        occupancy_prob = min(0.35, asset.traffic_per_day / 24.0 * 0.12)
        occupancy = (local.random(hours) < occupancy_prob).astype(float)
        partial = (local.random(hours) < partial_prob).astype(float)
        flicker = local.random(hours) < flicker_prob

        relay = np.empty(hours)
        drop_ms = np.empty(hours)
        pickup_ms = np.empty(hours)
        for index in range(hours):
            circuit = params.with_factors(
                rail_factor=float(rail_factor[index]),
                feed_factor=float(feed_factor[index]),
            )
            ballast = asset.dry_ballast_ohm_km * float(ballast_factor[index])
            occupied = bool(occupancy[index])
            current = relay_current(circuit, ballast, occupied=occupied)
            if partial[index] > 0:
                current *= 0.55
            relay[index] = current * 1000.0
            drop_ms[index] = 250.0 + timing_extra[index] + local.normal(0.0, 18.0)
            pickup_ms[index] = 300.0 + timing_extra[index] * 0.6 + local.normal(0.0, 20.0)

        # F12 / F2 flicker: short unexplained dropouts.
        relay = np.where(flicker, relay * local.uniform(0.45, 0.7, hours), relay)
        drop_ms = np.where(flicker, drop_ms + local.uniform(150.0, 500.0, hours), drop_ms)

        # Supply voltage and harmonic noise floor.
        feed = asset.feed_v * feed_factor + local.normal(0.0, 0.05, hours)
        harmonic_mv = 8.0 * harmonic + local.normal(0.0, 0.6, hours)
        neighbour_i = 55.0 * neighbour_factor + local.normal(0.0, 3.0, hours)
        cable_ir = 800.0 * cable_factor + local.normal(0.0, 18.0, hours)
        cable_ir = np.maximum(cable_ir, 5.0)

        # Measurement noise, outliers and quantisation.
        relay = relay * (1.0 + local.normal(0.0, 0.008, hours))
        outlier = local.random(hours) < 0.0015
        relay = np.where(outlier, relay * local.choice([0.55, 1.45], hours), relay)
        relay = np.round(relay, 1)
        feed = np.round(feed, 2)
        rain = np.round(rain, 2)

        # Logger gaps (>= 6 h), stuck runs (>= 30) and clock skew.
        injected: list[str] = []
        if local.random() < 0.30 and hours > 48:
            gap_start = int(local.integers(12, max(13, hours - 12)))
            gap_len = int(local.integers(7, 11)) * 24
            relay[gap_start : gap_start + gap_len] = np.nan
            feed[gap_start : gap_start + gap_len] = np.nan
            injected.append("logger_gap_6h")
        if local.random() < 0.22 and hours > 80:
            stuck_start = int(local.integers(24, hours - 50))
            stuck_len = int(local.integers(32, 42))
            relay[stuck_start : stuck_start + stuck_len] = relay[stuck_start]
            injected.append("stuck_value_run")
        if local.random() < 0.18:
            clock_offsets[asset.asset_id] = int(local.integers(18, 41))
            injected.append("clock_skew")

        series[asset.asset_id] = {
            "relay_i": relay,
            "feed_v": feed,
            "rain_mm": rain,
            "temp_c": temp,
            "humidity_pct": humidity,
            "neighbour_i": neighbour_i,
            "harmonic_mv": harmonic_mv,
            "occupancy": occupancy,
            "drop_ms": drop_ms,
            "pickup_ms": pickup_ms,
            "cable_ir": cable_ir,
        }
        if scenario.name == "masked-decay":
            # Axle counter stays healthy; the track circuit occasionally reports clear.
            axle = occupancy.copy()
            masked = (occupancy > 0) & (local.random(hours) < 0.5)
            series[asset.asset_id]["occupancy"] = np.where(masked, 0.0, occupancy)
            series[asset.asset_id]["axle_occupied"] = axle
        else:
            series[asset.asset_id]["axle_occupied"] = occupancy.copy()
        quality_injections[asset.asset_id] = injected

    # Ground-truth event times. For F1 the event is the actual drop-away day (first daily
    # median free-section relay current below 50% of dry), not a hand-entered label.
    events: list[BenchEvent] = []
    for asset in assets:
        if not asset.faulted or asset.event_mode is None:
            continue
        event_day = int(asset.event_day or scenario.event_day)
        if asset.event_mode == "F1":
            relay = series[asset.asset_id]["relay_i"]
            occupancy = series[asset.asset_id]["occupancy"]
            daily = []
            for day in range(scenario.days):
                block = relay[day * 24 : (day + 1) * 24]
                occ = occupancy[day * 24 : (day + 1) * 24]
                free = block[(occ < 0.5) & np.isfinite(block)]
                daily.append(float(np.median(free)) if free.size else float("nan"))
            dry_ma = 1000.0 * relay_current(asset.line_params(), None)
            for day, value in enumerate(daily):
                if np.isfinite(value) and value / dry_ma < 0.5:
                    event_day = day
                    break
        event_time = (start + timedelta(days=event_day)).strftime("%Y-%m-%dT%H:%M:%SZ")
        events.append(
            BenchEvent(
                asset_id=asset.asset_id,
                mode=asset.event_mode,
                event_day=event_day,
                event_time=event_time,
                smms_id=f"SMMS-{stable_id('event', scenario.name, seed, asset.asset_id, 8)}",
                outcome="Confirmed on site; relay drop-away"
                if asset.event_mode == "F1"
                else "Confirmed",
                confirmed_mode=asset.event_mode,
                station=asset.station,
                division=asset.division,
            )
        )

    manifest = build_manifest(
        scenario_manifest(),
        [seed],
        version=BENCH_VERSION,
        generator="nidan_ai.bench.generator/1",
    )
    return BenchStream(
        scenario=scenario.name,
        seed=seed,
        division=division or assets[0].division,
        assets=assets,
        timestamps=timestamps,
        series=series,
        events=events,
        manifest=manifest,
        scenario_def=scenario,
        clock_offsets_minutes=clock_offsets,
        quality_injections=quality_injections,
    )


def signal_names() -> tuple[str, ...]:
    """Canonical signal keys emitted by the bench (a subset of the telemetry contract)."""
    return SIGNAL_KEYS


def as_telemetry_samples(stream: BenchStream, *, asset_ids: list[str] | None = None) -> list[dict]:
    """Flatten a bench stream into canonical ``TelemetrySample`` dictionaries.

    This is the only place bench data becomes wire-shaped. It never writes to the backend.
    """
    selected = asset_ids or stream.asset_ids
    samples: list[dict[str, Any]] = []
    for asset_id in selected:
        asset_series = stream.series[asset_id]
        for index, timestamp in enumerate(stream.timestamps):
            for key, values in asset_series.items():
                value = float(values[index])
                if not np.isfinite(value):
                    continue
                samples.append(
                    {
                        "assetId": asset_id,
                        "signalKey": key,
                        "observedAt": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "value": value,
                        "quality": 0,
                        "source": "nidan-bench",
                    }
                )
    return samples
