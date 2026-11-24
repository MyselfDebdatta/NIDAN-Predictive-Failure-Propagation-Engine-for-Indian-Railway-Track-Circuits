"""Alert queue, detail, acknowledgement, and deferral service."""

from __future__ import annotations

from typing import Any

from app.middleware import ApiProblemException
from app.services.repository import NidanRepository
from app.services.stream_hub import StreamHub


class AlertService:
    """Orchestrates advisory alert reads and workflow state transitions."""

    def __init__(self, repo: NidanRepository, stream: StreamHub) -> None:
        self.repo = repo
        self.stream = stream

    async def list_alerts(self) -> list[dict[str, Any]]:
        return await self.repo.list_alerts()

    async def get_alert(self, alert_id: str) -> dict[str, Any]:
        alert = await self.repo.get_alert(alert_id)
        if alert is None:
            raise ApiProblemException(
                status=404,
                title="Alert not found",
                detail=f"Alert '{alert_id}' was not found.",
                error_type="urn:nidan:not-found",
            )
        return alert

    async def acknowledge_alert(self, alert_id: str) -> dict[str, Any]:
        result = await self.repo.acknowledge_alert(alert_id)
        if result is None:
            raise ApiProblemException(
                status=404,
                title="Alert not found",
                detail=f"Alert '{alert_id}' was not found.",
                error_type="urn:nidan:not-found",
            )
        alert = await self.repo.get_alert(result["alertId"])
        if alert is not None:
            await self.stream.publish(
                {
                    "type": "alert.upserted",
                    "alertId": alert["id"],
                    "level": alert["level"],
                    "assetId": alert["assetId"],
                    "snapshotId": "snap-2026-07-14T00:20Z",
                }
            )
        return result

    async def defer_alert(self, alert_id: str, *, reason: str, review_date: str) -> dict[str, Any]:
        result = await self.repo.defer_alert(alert_id, reason=reason, review_date=review_date)
        if result is None:
            raise ApiProblemException(
                status=404,
                title="Alert not found",
                detail=f"Alert '{alert_id}' was not found.",
                error_type="urn:nidan:not-found",
            )
        await self.stream.publish(
            {
                "type": "alert.closed",
                "alertId": result["alertId"],
                "outcome": "deferred",
            }
        )
        return result
