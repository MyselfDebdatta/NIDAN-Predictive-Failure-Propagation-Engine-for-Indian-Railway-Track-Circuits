"""Canonical telemetry and event loaders.

Two sources are supported: the deterministic bench and a read-only export/database. The
loader never writes telemetry. All timestamps are timezone-aware UTC; naive timestamps are
rejected, and series are sorted deterministically before any feature is computed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from nidan_ai.bench.generator import BenchStream


class NaiveTimestampError(ValueError):
    """Raised when a timestamp has no timezone; computation is always UTC."""


def parse_utc(value: datetime | str) -> datetime:
    """Parse an ISO timestamp and require an explicit timezone, returning UTC."""
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise NaiveTimestampError(f"Naive timestamp rejected: {value!r}")
    return parsed.astimezone(UTC)


@dataclass(slots=True)
class TelemetrySeries:
    """One asset/signal series sorted by observation time."""

    asset_id: str
    signal_key: str
    observed_at: list[datetime]
    values: np.ndarray
    quality: np.ndarray | None = None

    def __post_init__(self) -> None:
        order = sorted(range(len(self.observed_at)), key=lambda index: self.observed_at[index])
        self.observed_at = [self.observed_at[index] for index in order]
        self.values = np.asarray(self.values, dtype=float)[order]
        if self.quality is not None:
            self.quality = np.asarray(self.quality)[order]

    def between(self, start: datetime, end: datetime) -> tuple[np.ndarray, np.ndarray]:
        """Return values and a boolean mask for ``start <= t <= end``."""
        mask = np.array([start <= timestamp <= end for timestamp in self.observed_at], dtype=bool)
        return self.values[mask], mask


@dataclass(slots=True)
class AssetTelemetry:
    """All canonical series for one asset."""

    asset_id: str
    series: dict[str, TelemetrySeries]

    def signal(self, key: str) -> TelemetrySeries | None:
        return self.series.get(key)

    def values_until(self, key: str, as_of: datetime) -> tuple[np.ndarray, np.ndarray]:
        series = self.series.get(key)
        if series is None:
            return np.array([]), np.array([], dtype=bool)
        timestamps = np.array(series.observed_at, dtype=object)
        mask = np.array([timestamp <= as_of for timestamp in timestamps], dtype=bool)
        return series.values[mask], mask


@dataclass(slots=True)
class CanonicalDataset:
    """A snapshot-ready collection of asset telemetry plus ground-truth events."""

    assets: dict[str, AssetTelemetry]
    events: list[dict[str, Any]]
    source: str
    as_of: datetime

    def asset_ids(self) -> list[str]:
        return sorted(self.assets)


def from_bench(stream: BenchStream, *, as_of: datetime | None = None) -> CanonicalDataset:
    """Convert a bench stream into canonical series without any future samples."""
    resolved_as_of = as_of or stream.timestamps[-1]
    resolved_as_of = parse_utc(resolved_as_of)
    assets: dict[str, AssetTelemetry] = {}
    for asset in stream.assets:
        series_map: dict[str, TelemetrySeries] = {}
        for signal_key, values in stream.series[asset.asset_id].items():
            timestamps = [
                timestamp for timestamp in stream.timestamps if timestamp <= resolved_as_of
            ]
            trimmed = np.asarray(values[: len(timestamps)], dtype=float)
            series_map[signal_key] = TelemetrySeries(
                asset_id=asset.asset_id,
                signal_key=signal_key,
                observed_at=timestamps,
                values=trimmed,
            )
        assets[asset.asset_id] = AssetTelemetry(asset_id=asset.asset_id, series=series_map)
    events = [
        {
            "assetId": event.asset_id,
            "mode": event.mode,
            "eventDay": event.event_day,
            "eventTime": event.event_time,
            "smmsId": event.smms_id,
            "outcome": event.outcome,
            "confirmedMode": event.confirmed_mode,
            "station": event.station,
            "division": event.division,
        }
        for event in stream.events
    ]
    return CanonicalDataset(
        assets=assets,
        events=events,
        source=f"bench:{stream.scenario}:seed={stream.seed}",
        as_of=resolved_as_of,
    )


def _build_dataset_from_rows(
    rows: list[dict[str, Any]],
    *,
    source: str,
    as_of: datetime | str | None = None,
    events: list[dict[str, Any]] | None = None,
) -> CanonicalDataset:
    grouped: dict[tuple[str, str], list[tuple[datetime, float, int | None]]] = {}
    for row in rows:
        raw_obs = row["observedAt"]
        observed_at = raw_obs if isinstance(raw_obs, datetime) else parse_utc(raw_obs)
        if observed_at.tzinfo is None:
            observed_at = parse_utc(observed_at)
        key = (str(row["assetId"]), str(row["signalKey"]))
        quality = row.get("quality")
        grouped.setdefault(key, []).append(
            (observed_at, float(row["value"]), int(quality) if quality is not None else None)
        )
    resolved_as_of = (
        parse_utc(as_of)
        if as_of is not None
        else max(
            (item[0] for items in grouped.values() for item in items), default=datetime.now(UTC)
        )
    )
    assets: dict[str, AssetTelemetry] = {}
    for (asset_id, signal_key), items in grouped.items():
        items = [item for item in items if item[0] <= resolved_as_of]
        if not items:
            continue
        items.sort(key=lambda item: item[0])
        quality_values = (
            None
            if any(item[2] is None for item in items)
            else np.array([item[2] for item in items], dtype=int)
        )
        series = TelemetrySeries(
            asset_id=asset_id,
            signal_key=signal_key,
            observed_at=[item[0] for item in items],
            values=np.array([item[1] for item in items], dtype=float),
            quality=quality_values,
        )
        assets.setdefault(asset_id, AssetTelemetry(asset_id=asset_id, series={}))
        assets[asset_id].series[signal_key] = series
    return CanonicalDataset(
        assets=assets,
        events=list(events or []),
        source=source,
        as_of=resolved_as_of,
    )


def load_telemetry_export(
    path: str | Path,
    *,
    as_of: datetime | str | None = None,
    events_path: str | Path | None = None,
) -> CanonicalDataset:
    """Load a read-only JSON/JSONL export of canonical telemetry samples.

    Expected rows: ``{"assetId", "signalKey", "observedAt", "value", "quality"}``.
    The export is never modified; the loader only reads it.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Telemetry export not found: {source}")
    rows: list[dict[str, Any]] = []
    if source.suffix.lower() == ".jsonl":
        with source.open("r", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
    else:
        payload = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "samples" in payload:
            rows = list(payload["samples"])
        elif isinstance(payload, list):
            rows = payload
        else:
            raise ValueError("Telemetry export must be a list or an object with 'samples'")

    events: list[dict[str, Any]] = []
    if events_path is not None:
        event_file = Path(events_path)
        if event_file.exists():
            raw = json.loads(event_file.read_text(encoding="utf-8"))
            events = raw if isinstance(raw, list) else list(raw.get("events", []))
    return _build_dataset_from_rows(
        rows, source=f"export:{source.name}", as_of=as_of, events=events
    )


def load_readonly_database(dsn: str, *, as_of: datetime | str | None = None) -> CanonicalDataset:
    """Load telemetry from PostgreSQL in a read-only transaction.

    ``psycopg`` is supplied by the backend installation. This function issues only SELECTs;
    it has no write path and no connection to field equipment.
    """
    try:
        import psycopg  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - optional path
        raise RuntimeError("psycopg is required for --source db; install nidan-backend") from exc

    resolved_as_of = parse_utc(as_of) if as_of is not None else datetime.now(UTC)
    query = """
        select asset_id, signal_key, observed_at, value, quality
        from telemetry_reading
        where observed_at <= %s
        order by asset_id, signal_key, observed_at
    """
    rows: list[dict[str, Any]] = []
    with psycopg.connect(dsn, autocommit=False) as connection:
        with connection.cursor() as cursor:
            cursor.execute("set transaction read only")
            cursor.execute(query, (resolved_as_of,))
            for asset_id, signal_key, observed_at, value, quality in cursor.fetchall():
                rows.append(
                    {
                        "assetId": asset_id,
                        "signalKey": signal_key,
                        "observedAt": observed_at,
                        "value": value,
                        "quality": quality,
                    }
                )
    return _build_dataset_from_rows(rows, source="postgres-read-only", as_of=resolved_as_of)


def iter_samples(dataset: CanonicalDataset) -> Iterable[dict[str, Any]]:
    """Yield canonical wire samples for the two allowed ingest calls."""
    for asset_id in dataset.asset_ids():
        asset = dataset.assets[asset_id]
        for signal_key in sorted(asset.series):
            series = asset.series[signal_key]
            for index, timestamp in enumerate(series.observed_at):
                value = float(series.values[index])
                if not np.isfinite(value):
                    continue
                quality = int(series.quality[index]) if series.quality is not None else 0
                yield {
                    "assetId": asset_id,
                    "signalKey": signal_key,
                    "observedAt": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "value": value,
                    "quality": quality,
                    "source": "nidan-bench" if dataset.source.startswith("bench:") else "logger",
                }
