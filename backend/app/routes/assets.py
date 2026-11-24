"""Track-circuit asset detail, telemetry series, and three-lens explanation routes."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Response

from app.models.alerts import AssetExplanationResponse
from app.models.assets import AssetDetail
from app.routes.deps import get_asset_service
from app.services import AssetService

router = APIRouter(prefix="/v1/assets", tags=["assets"])


@router.get(
    "/{asset_id:path}/explanation",
    response_model=AssetExplanationResponse,
    response_model_by_alias=True,
)
async def get_asset_explanation(
    asset_id: str,
    response: Response,
    service: Annotated[AssetService, Depends(get_asset_service)],
):
    """Return the three-lens explanation (Physics / Model / Precedents) for an asset."""
    response.headers["Cache-Control"] = "private, max-age=30"
    return await service.get_asset_explanation(unquote(asset_id))


@router.get(
    "/{asset_id:path}",
    response_model=AssetDetail,
    response_model_by_alias=True,
)
async def get_asset_detail(
    asset_id: str,
    response: Response,
    service: Annotated[AssetService, Depends(get_asset_service)],
):
    """Return asset register metadata, 12-day telemetry series, mode set, and active alert."""
    response.headers["Cache-Control"] = "private, max-age=60"
    return await service.get_asset_detail(unquote(asset_id))
