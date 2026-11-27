"""Field tablet task retrieval and idempotent observation intake service."""

from __future__ import annotations

from typing import Any

from app.metrics import metrics_registry
from app.middleware import ApiProblemException
from app.services.repository import NidanRepository
from app.services.stream_hub import StreamHub


class FieldService:
    """Supports offline-first field PWA task sync and observation submission."""

    def __init__(self, repo: NidanRepository, stream: StreamHub) -> None:
        self.repo = repo
        self.stream = stream

    async def get_tasks(self) -> dict[str, Any]:
        return await self.repo.get_field_tasks()

    async def submit_observation(
        self, *, idempotency_key: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            receipt, replayed = await self.repo.submit_observation(
                idempotency_key=idempotency_key,
                payload=payload,
            )
        except ApiProblemException as exc:
            if exc.status == 409:
                metrics_registry.record_observation("conflict")
            raise
        metrics_registry.record_observation("replayed" if replayed else "created")
        if not replayed:
            await self.stream.publish(
                {
                    "type": "alert.upserted",
                    "alertId": payload["taskId"],
                    "level": "watch",
                    "assetId": payload["taskId"],
                    "snapshotId": "snap-2026-07-14T00:20Z",
                }
            )
        return receipt
