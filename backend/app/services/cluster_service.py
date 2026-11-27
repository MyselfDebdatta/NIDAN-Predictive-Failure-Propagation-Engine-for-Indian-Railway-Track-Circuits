"""Common-cause cluster query and merge service."""

from __future__ import annotations

from typing import Any

from app.middleware import ApiProblemException
from app.services.repository import NidanRepository
from app.services.stream_hub import StreamHub


class ClusterService:
    """Manages common-cause clusters derived from alert.clusterId."""

    def __init__(self, repo: NidanRepository, stream: StreamHub) -> None:
        self.repo = repo
        self.stream = stream

    async def list_clusters(self) -> list[dict[str, Any]]:
        return await self.repo.get_clusters()

    async def merge_cluster(
        self,
        cluster_id: str,
        alert_ids: list[str],
        *,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        result = await self.repo.merge_cluster(
            cluster_id,
            alert_ids,
            actor_sub=actor_sub,
            actor_role=actor_role,
            request_id=request_id,
        )
        if result is None:
            raise ApiProblemException(
                status=404,
                title="Cluster not found",
                detail=f"Cluster '{cluster_id}' was not found.",
                error_type="urn:nidan:not-found",
            )
        await self.stream.publish({"type": "cluster.updated", "clusterId": cluster_id})
        return result
