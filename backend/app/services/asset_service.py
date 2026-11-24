"""Asset detail, signal history, and three-lens explanation service."""

from __future__ import annotations

from typing import Any

from app.middleware import ApiProblemException
from app.models.common import ModelVersions, utc_now_iso
from app.services.repository import NidanRepository


class AssetService:
    """Reads track-circuit asset records, telemetry trends, and explanations."""

    def __init__(self, repo: NidanRepository) -> None:
        self.repo = repo

    async def get_asset_detail(self, asset_id: str) -> dict[str, Any]:
        detail = await self.repo.get_asset_detail(asset_id)
        if detail is None:
            raise ApiProblemException(
                status=404,
                title="Asset not found",
                detail=f"Track-circuit asset '{asset_id}' was not found.",
                error_type="urn:nidan:not-found",
            )
        return detail

    async def get_asset_explanation(self, asset_id: str) -> dict[str, Any]:
        detail = await self.get_asset_detail(asset_id)
        alert = detail.get("alert")
        if alert is None:
            raise ApiProblemException(
                status=404,
                title="Explanation not found",
                detail=f"No active assessment explanation exists for '{asset_id}'.",
                error_type="urn:nidan:not-found",
            )
        explanation = alert["explanation"]
        return {
            "alertId": alert["id"],
            "assetId": alert["assetId"],
            "physics": explanation["physics"],
            "model": explanation["model"],
            "precedents": explanation["precedents"],
            "modelVersions": alert.get("modelVersions")
            or ModelVersions().model_dump(by_alias=True),
            "generatedAt": utc_now_iso(),
        }
