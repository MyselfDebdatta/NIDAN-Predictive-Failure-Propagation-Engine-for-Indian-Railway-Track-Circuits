"""Repository protocol abstracting PostgreSQL and fixture-backed storage."""

from __future__ import annotations

from typing import Any, Protocol


class NidanRepository(Protocol):
    """Data-access interface shared by PostgreSQL and in-memory repositories."""

    async def list_alerts(self) -> list[dict[str, Any]]: ...

    async def get_alert(self, alert_id: str) -> dict[str, Any] | None: ...

    async def acknowledge_alert(self, alert_id: str) -> dict[str, Any] | None: ...

    async def defer_alert(
        self, alert_id: str, *, reason: str, review_date: str
    ) -> dict[str, Any] | None: ...

    async def get_asset_detail(self, asset_id: str) -> dict[str, Any] | None: ...

    async def get_blocks(self) -> dict[str, Any]: ...

    async def get_clusters(self) -> list[dict[str, Any]]: ...

    async def merge_cluster(
        self, cluster_id: str, alert_ids: list[str]
    ) -> dict[str, Any] | None: ...

    async def get_field_tasks(self) -> dict[str, Any]: ...

    async def submit_observation(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]: ...

    async def get_model_health(self) -> dict[str, Any]: ...

    async def get_kpi_summary(self) -> dict[str, Any]: ...

    async def create_work_order_draft(
        self, *, alert_id: str, action: str, block_id: str
    ) -> dict[str, Any] | None: ...

    async def search(self, query: str) -> list[dict[str, Any]]: ...
