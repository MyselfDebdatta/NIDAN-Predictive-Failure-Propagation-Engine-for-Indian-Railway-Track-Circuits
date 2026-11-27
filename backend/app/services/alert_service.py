"""Alert queue, detail, acknowledgement, deferral, and model-run publish service."""

from __future__ import annotations

from typing import Any

from app.metrics import metrics_registry
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

    async def acknowledge_alert(
        self,
        alert_id: str,
        *,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        result = await self.repo.acknowledge_alert(
            alert_id,
            actor_sub=actor_sub,
            actor_role=actor_role,
            request_id=request_id,
        )
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
                    "division": alert.get("division"),
                    "snapshotId": "snap-2026-07-14T00:20Z",
                }
            )
        return result

    async def defer_alert(
        self,
        alert_id: str,
        *,
        reason: str,
        review_date: str,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        result = await self.repo.defer_alert(
            alert_id,
            reason=reason,
            review_date=review_date,
            actor_sub=actor_sub,
            actor_role=actor_role,
            request_id=request_id,
        )
        if result is None:
            raise ApiProblemException(
                status=404,
                title="Alert not found",
                detail=f"Alert '{alert_id}' was not found.",
                error_type="urn:nidan:not-found",
            )
        alert = await self.repo.get_alert(result["alertId"])
        await self.stream.publish(
            {
                "type": "alert.closed",
                "alertId": result["alertId"],
                "division": alert.get("division") if alert else None,
                "outcome": "deferred",
            }
        )
        return result

    async def publish_model_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Publish a model-run snapshot atomically and record metrics."""
        try:
            result = await self.repo.publish_model_run(payload)
        except Exception:
            metrics_registry.record_model_run("failed")
            raise
        metrics_registry.record_model_run(
            "replayed" if result.get("idempotent_replay") else "succeeded"
        )
        return result
