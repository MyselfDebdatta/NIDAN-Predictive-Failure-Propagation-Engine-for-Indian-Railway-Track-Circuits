"""Canonical telemetry schemas and C-DOT CCSP / RDSO RDPMS adapters."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.models.common import CamelModel


def _parse_iso_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class TelemetrySample(CamelModel):
    """Single canonical telemetry measurement matching telemetry_reading."""

    asset_id: str = Field(min_length=3, max_length=64)
    signal_key: str = Field(min_length=2, max_length=40)
    observed_at: datetime
    value: float
    quality: Literal[0, 1, 2] | None = None
    source: str = Field(default="logger", min_length=1, max_length=64)

    @field_validator("observed_at", mode="before")
    @classmethod
    def _ensure_tz(cls, v: Any) -> datetime:
        return _parse_iso_dt(v)


class TelemetryBatchRequest(CamelModel):
    """Canonical batch payload accepted by POST /v1/ingest/telemetry."""

    samples: list[TelemetrySample] = Field(min_length=1, max_length=5000)
    source_protocol: Literal["canonical", "ccsp", "rdpms"] = "canonical"


class TelemetryIngestResponse(CamelModel):
    """Response summarizing ingested telemetry and stream QC counts."""

    accepted: int
    deduplicated: int
    measured_count: int
    interpolated_count: int
    suspect_count: int
    qc_flags_by_asset: dict[str, list[str]] = Field(default_factory=dict)
    trust_scores_by_asset: dict[str, float] = Field(default_factory=dict)
    generated_at: str


class CcspContentInstance(CamelModel):
    """C-DOT CCSP / oneM2M m2m:cin notification payload."""

    ri: str | None = None
    ct: str | None = None
    con: dict[str, Any] | str


class RdpmsFrame(CamelModel):
    """RDSO/SPN/257/2025 v2.0 RDPMS station logger telemetry frame."""

    station_code: str = Field(min_length=2, max_length=16)
    circuit_id: str = Field(min_length=2, max_length=64)
    timestamp: datetime
    signals: dict[str, float]
    quality: Literal[0, 1, 2] | None = None
    logger_id: str = "rdpms-v2"

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ensure_ts(cls, v: Any) -> datetime:
        return _parse_iso_dt(v)


_RDPMS_SIGNAL_ALIASES: dict[str, str] = {
    "relayCurrentMa": "relay_i",
    "relay_current": "relay_i",
    "relay_i": "relay_i",
    "ballastConductance": "ballast_g",
    "ballast_g": "ballast_g",
    "feedVoltage": "feed_v",
    "feed_v": "feed_v",
    "cableInsulationMohm": "cable_ir",
    "cable_ir": "cable_ir",
}


def normalize_ccsp_payload(raw: dict[str, Any]) -> TelemetryBatchRequest:
    """Normalize a C-DOT CCSP / oneM2M content-instance envelope into canonical samples."""
    cin_raw = raw.get("m2m:cin", raw)
    cin = CcspContentInstance.model_validate(cin_raw)
    con_data = json.loads(cin.con) if isinstance(cin.con, str) else cin.con

    if "samples" in con_data and isinstance(con_data["samples"], list):
        samples = [TelemetrySample.model_validate(item) for item in con_data["samples"]]
        return TelemetryBatchRequest(samples=samples, source_protocol="ccsp")

    asset_id = str(con_data["assetId"])
    observed_at = _parse_iso_dt(con_data.get("observedAt") or cin.ct or datetime.now(UTC))
    source = str(con_data.get("source", "ccsp-onem2m"))
    quality = con_data.get("quality")

    if "signals" in con_data and isinstance(con_data["signals"], dict):
        samples = [
            TelemetrySample(
                asset_id=asset_id,
                signal_key=_RDPMS_SIGNAL_ALIASES.get(str(k), str(k)),
                observed_at=observed_at,
                value=float(v),
                quality=quality,
                source=source,
            )
            for k, v in con_data["signals"].items()
        ]
    else:
        samples = [
            TelemetrySample(
                asset_id=asset_id,
                signal_key=_RDPMS_SIGNAL_ALIASES.get(
                    str(con_data["signalKey"]), str(con_data["signalKey"])
                ),
                observed_at=observed_at,
                value=float(con_data["value"]),
                quality=quality,
                source=source,
            )
        ]
    return TelemetryBatchRequest(samples=samples, source_protocol="ccsp")


def normalize_rdpms_payload(raw: dict[str, Any]) -> TelemetryBatchRequest:
    """Normalize an RDSO/SPN/257/2025 v2.0 RDPMS frame or frame list into canonical samples."""
    frames_raw = raw.get("frames") if isinstance(raw.get("frames"), list) else [raw]
    samples: list[TelemetrySample] = []
    for item in frames_raw:
        frame = RdpmsFrame.model_validate(item)
        asset_id = (
            frame.circuit_id
            if "/" in frame.circuit_id
            else f"{frame.station_code}/TC/{frame.circuit_id}"
        )
        for sig_key, val in frame.signals.items():
            samples.append(
                TelemetrySample(
                    asset_id=asset_id,
                    signal_key=_RDPMS_SIGNAL_ALIASES.get(sig_key, sig_key),
                    observed_at=frame.timestamp,
                    value=float(val),
                    quality=frame.quality,
                    source=frame.logger_id,
                )
            )
    return TelemetryBatchRequest(samples=samples, source_protocol="rdpms")
