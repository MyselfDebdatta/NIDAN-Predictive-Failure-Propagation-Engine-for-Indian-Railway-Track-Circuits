"""KPI summary, SMMS draft pre-fill, federated search, and user identity service."""

from __future__ import annotations

from typing import Any

from app.middleware import ApiProblemException
from app.models.common import ModelVersions, utc_now_iso
from app.services.repository import NidanRepository


class SummaryService:
    """Provides division KPIs, draft SMMS work orders, search, and session context."""

    def __init__(self, repo: NidanRepository) -> None:
        self.repo = repo

    async def get_kpis(self) -> dict[str, Any]:
        return await self.repo.get_kpi_summary()

    async def create_work_order_draft(
        self, *, alert_id: str, action: str, block_id: str
    ) -> dict[str, Any]:
        draft = await self.repo.create_work_order_draft(
            alert_id=alert_id,
            action=action,
            block_id=block_id,
        )
        if draft is None:
            raise ApiProblemException(
                status=404,
                title="Alert not found",
                detail=f"Cannot draft work order: alert '{alert_id}' was not found.",
                error_type="urn:nidan:not-found",
            )
        return draft

    async def search(self, query: str) -> dict[str, Any]:
        hits = await self.repo.search(query)
        return {
            "query": query,
            "hits": hits,
            "modelVersions": ModelVersions().model_dump(by_alias=True),
            "generatedAt": utc_now_iso(),
        }

    async def get_me(self) -> dict[str, Any]:
        return {
            "userId": "de602e5e-03fe-53f6-a9f6-4d4621a2d040",
            "displayName": "SSE (Sig) Control — Adra",
            "role": "operator",
            "divisions": ["ADRA", "BKSC", "KGP", "TATA"],
            "advisoryOnly": True,
            "vitalCommandCapable": False,
            "capabilities": [
                "alerts.read",
                "alerts.acknowledge",
                "alerts.defer",
                "clusters.merge",
                "work_orders.draft",
                "field.observations.submit",
            ],
            "modelVersions": ModelVersions().model_dump(by_alias=True),
            "generatedAt": utc_now_iso(),
        }
