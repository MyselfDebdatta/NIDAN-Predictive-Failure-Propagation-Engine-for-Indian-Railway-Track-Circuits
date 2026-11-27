"""Async telemetry ingestion processor and MQTT / Kafka consumer adapters."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Literal

from app.cache import RedisCache
from app.ingestion.qc import evaluate_sample_qc
from app.ingestion.schemas import (
    TelemetryBatchRequest,
    normalize_ccsp_payload,
    normalize_rdpms_payload,
)
from app.metrics import metrics_registry
from app.models.common import utc_now_iso
from app.services.repository import NidanRepository
from app.services.stream_hub import StreamHub

logger = logging.getLogger("nidan.ingestion")

_QUALITY_LABELS: dict[int, str] = {
    0: "measured",
    1: "interpolated",
    2: "suspect",
}


class TelemetryIngestProcessor:
    """Normalizes, runs Stream QC, persists telemetry_reading rows, and notifies subscribers."""

    def __init__(
        self,
        repo: NidanRepository,
        *,
        stream_hub: StreamHub | None = None,
        cache: RedisCache | None = None,
    ) -> None:
        self.repo = repo
        self.stream_hub = stream_hub
        self.cache = cache

    async def process_raw(
        self,
        raw_payload: dict[str, Any],
        *,
        protocol: Literal["canonical", "ccsp", "rdpms"] = "canonical",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Normalize raw adapter payload, apply Stream QC, and persist."""
        if protocol == "ccsp":
            batch = normalize_ccsp_payload(raw_payload)
        elif protocol == "rdpms":
            batch = normalize_rdpms_payload(raw_payload)
        else:
            batch = TelemetryBatchRequest.model_validate(raw_payload)
        return await self.process_batch(batch, now=now)

    async def process_batch(
        self,
        batch: TelemetryBatchRequest,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Run Stream QC over canonical samples, write to repository, and record metrics."""
        qc_result = evaluate_sample_qc(batch.samples, now=now or datetime.now(UTC))

        rows = [
            {
                "assetId": s.asset_id,
                "signalKey": s.signal_key,
                "observedAt": s.observed_at,
                "value": s.value,
                "quality": s.quality if s.quality is not None else 0,
                "source": s.source,
            }
            for s in qc_result.samples
        ]

        counts = await self.repo.ingest_telemetry(rows)

        measured = sum(1 for r in rows if r["quality"] == 0)
        interpolated = sum(1 for r in rows if r["quality"] == 1)
        suspect = sum(1 for r in rows if r["quality"] == 2)

        if measured:
            metrics_registry.record_telemetry(_QUALITY_LABELS[0], measured)
        if interpolated:
            metrics_registry.record_telemetry(_QUALITY_LABELS[1], interpolated)
        if suspect:
            metrics_registry.record_telemetry(_QUALITY_LABELS[2], suspect)

        if self.cache is not None:
            await self.cache.invalidate_prefixes("assets:")

        if self.stream_hub is not None and counts["accepted"] > 0:
            for asset_id in sorted({r["assetId"] for r in rows}):
                await self.stream_hub.publish(
                    {
                        "type": "telemetry.ingested",
                        "assetId": asset_id,
                        "at": utc_now_iso(),
                    }
                )

        return {
            "accepted": counts["accepted"],
            "deduplicated": counts["deduplicated"],
            "measuredCount": measured,
            "interpolatedCount": interpolated,
            "suspectCount": suspect,
            "qcFlagsByAsset": qc_result.flags_by_asset,
            "trustScoresByAsset": qc_result.trust_by_asset,
            "generatedAt": utc_now_iso(),
        }


class KafkaTelemetryConsumer:
    """Async Kafka consumer adapter (requires optional aiokafka package at runtime)."""

    def __init__(
        self,
        processor: TelemetryIngestProcessor,
        *,
        bootstrap_servers: str,
        topic: str = "nidan.telemetry.raw",
        group_id: str = "nidan-telemetry-ingestor",
        protocol: Literal["canonical", "ccsp", "rdpms"] = "canonical",
    ) -> None:
        self.processor = processor
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.protocol = protocol

    async def handle_message_bytes(self, payload: bytes) -> dict[str, Any]:
        """Decode one Kafka message payload and run QC + repository ingest."""
        data = json.loads(payload.decode("utf-8"))
        return await self.processor.process_raw(data, protocol=self.protocol)

    async def run_forever(self) -> None:  # pragma: no cover - requires live Kafka broker
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "aiokafka is not installed; install aiokafka to run KafkaTelemetryConsumer."
            ) from exc

        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=False,
        )
        await consumer.start()
        try:
            async for msg in consumer:
                await self.handle_message_bytes(msg.value)
                await consumer.commit()
        finally:
            await consumer.stop()


class MqttTelemetryConsumer:
    """Async MQTT TLS subscriber adapter (requires optional aiomqtt package at runtime)."""

    def __init__(
        self,
        processor: TelemetryIngestProcessor,
        *,
        hostname: str,
        port: int = 8883,
        topic: str = "nidan/+/telemetry",
        protocol: Literal["canonical", "ccsp", "rdpms"] = "ccsp",
    ) -> None:
        self.processor = processor
        self.hostname = hostname
        self.port = port
        self.topic = topic
        self.protocol = protocol

    async def handle_message_bytes(self, payload: bytes) -> dict[str, Any]:
        """Decode one MQTT payload and run QC + repository ingest."""
        data = json.loads(payload.decode("utf-8"))
        return await self.processor.process_raw(data, protocol=self.protocol)

    async def run_forever(self) -> None:  # pragma: no cover - requires live MQTT broker
        try:
            import aiomqtt  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "aiomqtt is not installed; install aiomqtt to run MqttTelemetryConsumer."
            ) from exc

        async with aiomqtt.Client(hostname=self.hostname, port=self.port) as client:
            await client.subscribe(self.topic)
            async for message in client.messages:
                if isinstance(message.payload, (bytes, bytearray)):
                    await self.handle_message_bytes(bytes(message.payload))
